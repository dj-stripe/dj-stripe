# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import decimal
import json
import traceback as exception_traceback
import warnings
import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible, smart_text

from jsonfield.fields import JSONField
from model_utils.models import TimeStampedModel
import stripe

from . import settings as djstripe_settings
from . import webhooks
from .exceptions import SubscriptionCancellationFailure, SubscriptionUpdateFailure
from .managers import CustomerManager, ChargeManager, TransferManager
from .signals import WEBHOOK_SIGNALS
from .signals import subscription_made, cancelled, card_changed
from .signals import webhook_processing_error
from .stripe_objects import StripeEvent, StripeTransfer, StripeCustomer, StripeInvoice, StripeCharge, StripePlan, convert_tstamp

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = getattr(settings, "STRIPE_API_VERSION", "2012-11-07")


@python_2_unicode_compatible
class EventProcessingException(TimeStampedModel):
    """Tracks processing exceptions, storing Stack traces for easy reference
        in the admin interface.
    """

    event = models.ForeignKey("Event", null=True)
    data = models.TextField()
    message = models.CharField(max_length=500)
    traceback = models.TextField()

    @classmethod
    def log(cls, data, exception, event):
        """ Creates an instance of this model and saves it to the database.
            :param data: The `http_body` of a `StripeException`
            :param exception: An instance of `StripeException`
            :param event: An instance of `Event`
        """
        cls.objects.create(
            event=event,
            data=data or "",
            message=str(exception),
            traceback=exception_traceback.format_exc()
        )

    def __str__(self):
        return "<{message}, pk={pk}, Event={event}>".format(message=self.message, pk=self.pk, event=self.event)


class Event(StripeEvent):
    customer = models.ForeignKey("Customer", null=True)
    validated_message = JSONField(null=True)
    valid = models.NullBooleanField(null=True)
    processed = models.BooleanField(default=False)

    @property
    def message(self):
        return self.validated_message

    def validate(self):
        event = self.api_retrieve()
        self.validated_message = json.loads(
            json.dumps(
                event.to_dict(),
                sort_keys=True,
                cls=stripe.StripeObjectEncoder
            )
        )
        self.valid = self.webhook_message["data"] == self.validated_message["data"]
        self.save()

    def process(self):
        """
        Call whatever webhook event handlers have registered for this event, based on event "type" and
        event "sub type"

        See event handlers registered in djstripe.event_handlers module (or handlers registered in djstripe plugins or
        contrib packages)
        """
        if self.valid and not self.processed:
            event_type, event_subtype = self.kind.split(".", 1)

            try:
                # TODO: would it make sense to wrap the next 4 lines in a transaction.atomic context? Yes it would,
                # except that some webhook handlers can have side effects outside of our local database, meaning that
                # even if we rollback on our database, some updates may have been sent to Stripe, etc in resposne to
                # webhooks...
                webhooks.call_handlers(self, self.message["data"], event_type, event_subtype)
                self.send_signal()
                self.processed = True
                self.save()
            except stripe.StripeError as exc:
                # TODO: What if we caught all exceptions or a broader range of exceptions here? How about DoesNotExist
                # exceptions, for instance? or how about TypeErrors, KeyErrors, ValueErrors, etc?
                EventProcessingException.log(
                    data=exc.http_body,
                    exception=exc,
                    event=self
                )
                webhook_processing_error.send(
                    sender=Event,
                    data=exc.http_body,
                    exception=exc
                )

    def send_signal(self):
        signal = WEBHOOK_SIGNALS.get(self.kind)
        if signal:
            return signal.send(sender=Event, event=self)


class Transfer(StripeTransfer):
    event = models.ForeignKey(Event, related_name="transfers")

    objects = TransferManager()

    @classmethod
    def process_transfer(cls, event, stripe_object):
        try:
            transfer = cls.stripe_objects.get_by_json(stripe_object)
            created = False
        except cls.DoesNotExist:
            transfer = cls.create_from_stripe_object(stripe_object)
            created = True

        transfer.event = event

        if created:
            transfer.save()
            for fee in stripe_object["summary"]["charge_fee_details"]:
                transfer.charge_fee_details.create(
                    amount=fee["amount"] / decimal.Decimal("100"),
                    application=fee.get("application", ""),
                    description=fee.get("description", ""),
                    kind=fee["type"]
                )
        else:
            transfer.status = stripe_object["status"]
            transfer.save()

        if event and event.kind == "transfer.updated":
            transfer.update_status()
            transfer.save()


class TransferChargeFee(TimeStampedModel):
    transfer = models.ForeignKey(Transfer, related_name="charge_fee_details")
    amount = models.DecimalField(decimal_places=2, max_digits=7)
    application = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    kind = models.CharField(max_length=150)


class Customer(StripeCustomer):
    subscriber = models.OneToOneField(getattr(settings, 'DJSTRIPE_SUBSCRIBER_MODEL', settings.AUTH_USER_MODEL), null=True)
    date_purged = models.DateTimeField(null=True, editable=False)

    objects = CustomerManager()

    def purge(self):
        try:
            self.stripe_customer.delete()
        except stripe.InvalidRequestError as exc:
            if str(exc).startswith("No such customer:"):
                # The exception was thrown because the stripe customer was already
                # deleted on the stripe side, ignore the exception
                pass
            else:
                # The exception was raised for another reason, re-raise it
                raise
        self.subscriber = None
        super(Customer, self).purge()
        self.date_purged = timezone.now()
        self.save()

    def str_parts(self):
        return [
            smart_text(self.subscriber),
            "email={email}".format(email=self.subscriber.email),
        ] + super(Customer, self).str_parts()

    def delete(self, using=None):
        # Only way to delete a customer is to use SQL
        self.purge()

    def can_charge(self):
        return self.has_valid_card() and self.date_purged is None

    def has_active_subscription(self):
        try:
            return self.current_subscription.is_valid()
        except CurrentSubscription.DoesNotExist:
            return False

    def cancel_subscription(self, at_period_end=True):
        try:
            current_subscription = self.current_subscription
        except CurrentSubscription.DoesNotExist:
            raise SubscriptionCancellationFailure("Customer does not have current subscription")

        try:
            """
            If plan has trial days and customer cancels before trial period ends,
            then end subscription now, i.e. at_period_end=False
            """
            if self.current_subscription.trial_end and self.current_subscription.trial_end > timezone.now():
                at_period_end = False
            stripe_subscription = self.stripe_customer.cancel_subscription(at_period_end=at_period_end)
        except stripe.InvalidRequestError as exc:
            raise SubscriptionCancellationFailure("Customer's information is not current with Stripe.\n{}".format(str(exc)))

        current_subscription.status = stripe_subscription.status
        current_subscription.cancel_at_period_end = stripe_subscription.cancel_at_period_end
        current_subscription.current_period_end = convert_tstamp(stripe_subscription, "current_period_end")
        current_subscription.canceled_at = convert_tstamp(stripe_subscription, "canceled_at") or timezone.now()
        current_subscription.save()
        cancelled.send(sender=self, stripe_response=stripe_subscription)
        return current_subscription

    def cancel(self, at_period_end=True):
        warnings.warn("Deprecated - Use ``cancel_subscription`` instead. This method will be removed in dj-stripe 1.0.", DeprecationWarning)
        return self.cancel_subscription(at_period_end=at_period_end)

    @classmethod
    def get_or_create(cls, subscriber):
        try:
            return Customer.objects.get(subscriber=subscriber), False
        except Customer.DoesNotExist:
            return cls.create(subscriber), True

    @classmethod
    def create(cls, subscriber):
        trial_days = None
        if djstripe_settings.trial_period_for_subscriber_callback:
            trial_days = djstripe_settings.trial_period_for_subscriber_callback(subscriber)

        stripe_customer = cls.api_create(email=subscriber.email)
        customer = Customer.objects.create(subscriber=subscriber, stripe_id=stripe_customer.id)

        if djstripe_settings.DEFAULT_PLAN and trial_days:
            customer.subscribe(plan=djstripe_settings.DEFAULT_PLAN, trial_days=trial_days)

        return customer

    def update_card(self, token):
        # send new token to Stripe
        stripe_customer = self.stripe_customer
        stripe_customer.card = token
        stripe_customer.save()

        # Download new card details from Stripe
        self.sync_card()

        self.save()
        card_changed.send(sender=self, stripe_response=stripe_customer)

    def retry_unpaid_invoices(self):
        self.sync_invoices()
        for inv in self.invoices.filter(paid=False, closed=False):
            try:
                inv.retry()  # Always retry unpaid invoices
            except stripe.InvalidRequestError as exc:
                if str(exc) != "Invoice is already paid":
                    raise exc

    def send_invoice(self):
        try:
            invoice = Invoice.api_create(customer=self.stripe_id)
            invoice.pay()
            return True
        except stripe.InvalidRequestError:
            return False  # There was nothing to invoice

    # TODO refactor, deprecation on cu parameter -> stripe_customer
    def sync(self, cu=None):
        super(Customer, self).sync(cu)
        self.save()

    # TODO refactor, deprecation on cu parameter -> stripe_customer
    def sync_invoices(self, cu=None, **kwargs):
        stripe_customer = cu or self.stripe_customer
        for invoice in stripe_customer.invoices(**kwargs).data:
            Invoice.sync_from_stripe_data(invoice, send_receipt=False)

    # TODO refactor, deprecation on cu parameter -> stripe_customer
    def sync_charges(self, cu=None, **kwargs):
        stripe_customer = cu or self.stripe_customer
        for charge in stripe_customer.charges(**kwargs).data:
            self.record_charge(charge.id)

    # TODO refactor, deprecation on cu parameter -> stripe_customer
    def sync_current_subscription(self, cu=None):
        stripe_customer = cu or self.stripe_customer
        stripe_subscription = getattr(stripe_customer, 'subscription', None)
        current_subscription = getattr(self, 'current_subscription', None)

        if stripe_subscription:
            if current_subscription:
                logger.debug('Updating subscription')
                current_subscription.plan = djstripe_settings.plan_from_stripe_id(stripe_subscription.plan.id)
                current_subscription.current_period_start = convert_tstamp(
                    stripe_subscription.current_period_start
                )
                current_subscription.current_period_end = convert_tstamp(
                    stripe_subscription.current_period_end
                )
                current_subscription.amount = (stripe_subscription.plan.amount / decimal.Decimal("100"))
                current_subscription.status = stripe_subscription.status
                current_subscription.cancel_at_period_end = stripe_subscription.cancel_at_period_end
                current_subscription.canceled_at = convert_tstamp(stripe_subscription, "canceled_at")
                current_subscription.start = convert_tstamp(stripe_subscription.start)
                current_subscription.quantity = stripe_subscription.quantity
                current_subscription.save()
            else:
                logger.debug('Creating subscription')
                current_subscription = CurrentSubscription.objects.create(
                    customer=self,
                    plan=djstripe_settings.plan_from_stripe_id(stripe_subscription.plan.id),
                    current_period_start=convert_tstamp(
                        stripe_subscription.current_period_start
                    ),
                    current_period_end=convert_tstamp(
                        stripe_subscription.current_period_end
                    ),
                    amount=(stripe_subscription.plan.amount / decimal.Decimal("100")),
                    status=stripe_subscription.status,
                    cancel_at_period_end=stripe_subscription.cancel_at_period_end,
                    canceled_at=convert_tstamp(stripe_subscription, "canceled_at"),
                    start=convert_tstamp(stripe_subscription.start),
                    quantity=stripe_subscription.quantity
                )

            if stripe_subscription.trial_start and stripe_subscription.trial_end:
                current_subscription.trial_start = convert_tstamp(stripe_subscription.trial_start)
                current_subscription.trial_end = convert_tstamp(stripe_subscription.trial_end)
            else:
                """
                Avoids keeping old values for trial_start and trial_end
                for cases where customer had a subscription with trial days
                then one without that (s)he cancels.
                """
                current_subscription.trial_start = None
                current_subscription.trial_end = None

            current_subscription.save()

            return current_subscription
        elif current_subscription and current_subscription.status != CurrentSubscription.STATUS_CANCELLED:
            # Stripe says customer has no subscription but we think they have one.
            # This could happen if subscription is cancelled from Stripe Dashboard and webhook fails
            logger.debug('Cancelling subscription for %s' % self)
            current_subscription.status = CurrentSubscription.STATUS_CANCELLED
            current_subscription.save()
            return current_subscription

    def update_plan_quantity(self, quantity, charge_immediately=False):
        stripe_subscription = self.stripe_customer.subscription
        if not stripe_subscription:
            self.sync_current_subscription()
            raise SubscriptionUpdateFailure("Customer does not have a subscription with Stripe")
        self.subscribe(
            plan=djstripe_settings.plan_from_stripe_id(stripe_subscription.plan.id),
            quantity=quantity,
            charge_immediately=charge_immediately
        )

    def subscribe(self, plan, quantity=1, trial_days=None,
                  charge_immediately=True, prorate=djstripe_settings.PRORATION_POLICY):
        stripe_customer = self.stripe_customer
        """
        Trial_days corresponds to the value specified by the selected plan
        for the key trial_period_days.
        """
        if ("trial_period_days" in djstripe_settings.PAYMENTS_PLANS[plan]):
            trial_days = djstripe_settings.PAYMENTS_PLANS[plan]["trial_period_days"]

        if trial_days:
            resp = stripe_customer.update_subscription(
                plan=djstripe_settings.PAYMENTS_PLANS[plan]["stripe_plan_id"],
                trial_end=timezone.now() + datetime.timedelta(days=trial_days),
                prorate=prorate,
                quantity=quantity
            )
        else:
            resp = stripe_customer.update_subscription(
                plan=djstripe_settings.PAYMENTS_PLANS[plan]["stripe_plan_id"],
                prorate=prorate,
                quantity=quantity
            )
        self.sync_current_subscription()
        if charge_immediately:
            self.send_invoice()
        subscription_made.send(sender=self, plan=plan, stripe_response=resp)

    def charge(self, amount, currency="usd", description=None, send_receipt=True, **kwargs):
        """
        This method expects `amount` to be a Decimal type representing a
        dollar amount. It will be converted to cents so any decimals beyond
        two will be ignored.
        """
        charge_id = super(Customer, self).charge(amount, currency, description, send_receipt, **kwargs)
        recorded_charge = self.record_charge(charge_id)
        if send_receipt:
            recorded_charge.send_receipt()
        return recorded_charge

    def record_charge(self, charge_id):
        data = Charge.api().retrieve(charge_id)
        return Charge.sync_from_stripe_data(data)


class CurrentSubscription(TimeStampedModel):
    STATUS_TRIALING = "trialing"
    STATUS_ACTIVE = "active"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELLED = "canceled"
    STATUS_UNPAID = "unpaid"

    customer = models.OneToOneField(
        Customer,
        related_name="current_subscription",
        null=True
    )
    plan = models.CharField(max_length=100)
    quantity = models.IntegerField()
    start = models.DateTimeField()
    # trialing, active, past_due, canceled, or unpaid
    # In progress of moving it to choices field
    status = models.CharField(max_length=25)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True)
    current_period_start = models.DateTimeField(null=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    trial_start = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(decimal_places=2, max_digits=7)

    def plan_display(self):
        return djstripe_settings.PAYMENTS_PLANS[self.plan]["name"]

    def status_display(self):
        return self.status.replace("_", " ").title()

    def is_period_current(self):
        if self.current_period_end is None:
            return False
        return self.current_period_end > timezone.now()

    def is_status_current(self):
        return self.status in [self.STATUS_TRIALING, self.STATUS_ACTIVE]

    def is_status_temporarily_current(self):
        """
        Status when customer canceled their latest subscription, one that does not prorate,
        and therefore has a temporary active subscription until period end.
        """

        return self.canceled_at and self.start < self.canceled_at and self.cancel_at_period_end

    def is_valid(self):
        if not self.is_status_current():
            return False

        if self.cancel_at_period_end and not self.is_period_current():
            return False

        return True

    def extend(self, delta):
        if delta.total_seconds() < 0:
            raise ValueError("delta should be a positive timedelta.")

        period_end = None

        if self.trial_end is not None and \
           self.trial_end > timezone.now():
            period_end = self.trial_end
        else:
            period_end = self.current_period_end

        period_end += delta

        self.customer.stripe_customer.update_subscription(
            prorate=False,
            trial_end=period_end,
        )

        self.customer.sync_current_subscription()


class Invoice(StripeInvoice):

    customer = models.ForeignKey(Customer, related_name="invoices")

    class Meta:
        ordering = ["-date"]

    @classmethod
    def sync_from_stripe_data(cls, stripe_invoice, send_receipt=True):
        customer = Customer.objects.get(stripe_id=stripe_invoice["customer"])

        try:
            invoice = cls.stripe_objects.get_by_json(stripe_invoice)
            created = False
        except cls.DoesNotExist:
            invoice = cls.create_from_stripe_object(stripe_invoice)
            invoice.customer = customer
            created = True

        if not created:
            # update all fields using the stripe data
            invoice.sync(cls.stripe_object_to_record(stripe_invoice))

        invoice.save()

        for item in stripe_invoice["lines"].get("data", []):
            period_end = convert_tstamp(item["period"], "end")
            period_start = convert_tstamp(item["period"], "start")
            """
            Period end of invoice is the period end of the latest invoiceitem.
            """
            invoice.period_end = period_end

            if item.get("plan"):
                plan = djstripe_settings.plan_from_stripe_id(item["plan"]["id"])
            else:
                plan = ""

            inv_item, inv_item_created = invoice.items.get_or_create(
                stripe_id=item["id"],
                defaults=dict(
                    amount=(item["amount"] / decimal.Decimal("100")),
                    currency=item["currency"],
                    proration=item["proration"],
                    description=item.get("description") or "",
                    line_type=item["type"],
                    plan=plan,
                    period_start=period_start,
                    period_end=period_end,
                    quantity=item.get("quantity")
                )
            )
            if not inv_item_created:
                inv_item.amount = (item["amount"] / decimal.Decimal("100"))
                inv_item.currency = item["currency"]
                inv_item.proration = item["proration"]
                inv_item.description = item.get("description") or ""
                inv_item.line_type = item["type"]
                inv_item.plan = plan
                inv_item.period_start = period_start
                inv_item.period_end = period_end
                inv_item.quantity = item.get("quantity")
                inv_item.save()

        """
        Save invoice period end assignment.
        """
        invoice.save()

        if stripe_invoice.get("charge"):
            recorded_charge = customer.record_charge(stripe_invoice["charge"])
            recorded_charge.invoice = invoice
            recorded_charge.save()
            if send_receipt:
                recorded_charge.send_receipt()
        return invoice


class InvoiceItem(TimeStampedModel):
    """
    Not inherited from StripeObject because there can be multiple invoice
    items for a single stripe_id.
    """

    stripe_id = models.CharField(max_length=50)
    invoice = models.ForeignKey(Invoice, related_name="items")
    amount = models.DecimalField(decimal_places=2, max_digits=7)
    currency = models.CharField(max_length=10)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    proration = models.BooleanField(default=False)
    line_type = models.CharField(max_length=50)
    description = models.CharField(max_length=200, blank=True)
    plan = models.CharField(max_length=100, null=True, blank=True)
    quantity = models.IntegerField(null=True)

    def __str__(self):
        return "<amount={amount}, plan={plan}, stripe_id={stripe_id}>".format(amount=self.amount, plan=smart_text(self.plan), stripe_id=self.stripe_id)

    def plan_display(self):
        return djstripe_settings.PAYMENTS_PLANS[self.plan]["name"]


class Charge(StripeCharge):
    stripe_api_name = "Charge"

    customer = models.ForeignKey(Customer, related_name="charges")
    invoice = models.ForeignKey(Invoice, null=True, related_name="charges")

    objects = ChargeManager()

    def refund(self, amount=None, **kwargs):
        """
        Refund an existing charge https://stripe.com/docs/api#create_refund
        Stripe Connect information https://stripe.com/docs/connect/payments-fees#issuing-refunds
        """
        refunded_charge = super(Charge, self).refund(amount, **kwargs)
        return Charge.sync_from_stripe_data(refunded_charge)

    def capture(self):
        """
        Capture the payment of an existing, uncaptured, charge. This is the second half of the two-step payment flow,
        where first you created a charge with the capture option set to false.
        See https://stripe.com/docs/api#capture_charge
        """
        captured_charge = super(Charge, self).capture()
        return Charge.sync_from_stripe_data(captured_charge)

    @classmethod
    def sync_from_stripe_data(cls, data):

        try:
            charge = cls.stripe_objects.get_by_json(data)
            charge.sync(cls.stripe_object_to_record(data))
        except cls.DoesNotExist:
            charge = cls.create_from_stripe_object(data)

        customer = cls.object_to_customer(Customer.stripe_objects, data)
        charge.customer = customer

        try:
            invoice = cls.object_to_invoice(Invoice.stripe_objects, data)
            if invoice:
                charge.invoice = invoice
        except Invoice.DoesNotExist:
            logger.warning("No invoice {0} found for charge {1}".format(data.get('invoice'), data.get('id')))

        charge.save()
        return charge

    def send_receipt(self):
        if not self.receipt_sent:
            site = Site.objects.get_current()
            protocol = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")
            ctx = {
                "charge": self,
                "site": site,
                "protocol": protocol,
            }
            subject = render_to_string("djstripe/email/subject.txt", ctx)
            subject = subject.strip()
            message = render_to_string("djstripe/email/body.txt", ctx)
            num_sent = EmailMessage(
                subject,
                message,
                to=[self.customer.subscriber.email],
                from_email=djstripe_settings.INVOICE_FROM_EMAIL
            ).send()
            self.receipt_sent = num_sent > 0
            self.save()


INTERVALS = (
    ('week', 'Week',),
    ('month', 'Month',),
    ('year', 'Year',))


class Plan(StripePlan):
    """A Stripe Plan."""

    name = models.CharField(max_length=100, null=False)
    currency = models.CharField(
        choices=djstripe_settings.CURRENCIES,
        max_length=10,
        null=False)
    interval = models.CharField(
        max_length=10,
        choices=INTERVALS,
        verbose_name="Interval type",
        null=False)
    interval_count = models.IntegerField(
        verbose_name="Intervals between charges",
        default=1,
        null=True)
    amount = models.DecimalField(decimal_places=2, max_digits=7,
                                 verbose_name="Amount (per period)",
                                 null=False)
    trial_period_days = models.IntegerField(null=True)

    def str_parts(self):
        return [smart_text(self.name)] + super(Plan, self).str_parts()

    @classmethod
    def create(cls, **kwargs):

        # A few minor things are changed in the api-version of the create call
        api_kwargs = dict(kwargs)
        api_kwargs['id'] = api_kwargs['stripe_id']
        del(api_kwargs['stripe_id'])
        api_kwargs['amount'] = int(api_kwargs['amount'] * 100)
        cls.api_create(**api_kwargs)

        # If they passed in a 'metadata' arg, drop that here as it is only for api consumption
        if 'metadata' in kwargs:
            del(kwargs['metadata'])
        plan = Plan.objects.create(**kwargs)

        return plan

    @classmethod
    def get_or_create(cls, **kwargs):
        try:
            return Plan.objects.get(stripe_id=kwargs['stripe_id']), False
        except Plan.DoesNotExist:
            return cls.create(**kwargs), True

    def update_name(self):
        """Update the name of the Plan in Stripe and in the db.

        - Assumes the object being called has the name attribute already
          reset, but has not been saved.
        - Stripe does not allow for update of any other Plan attributes besides
          name.

        """

        p = self.api_retrieve()
        p.name = self.name
        p.save()

        self.save()

# Much like registering signal handlers. We import this module so that its registrations get picked up
# the NO QA directive tells flake8 to not complain about the unused import
from . import event_handlers  # NOQA
