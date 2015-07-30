# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import decimal
import json
import traceback as exception_traceback
import warnings

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
from .exceptions import SubscriptionCancellationFailure, SubscriptionApiError
from .managers import CustomerManager, ChargeManager, TransferManager
from .signals import WEBHOOK_SIGNALS
from .signals import subscription_made, cancelled, card_changed
from .signals import webhook_processing_error


stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = getattr(settings, "STRIPE_API_VERSION", "2014-01-31")


def convert_tstamp(response, field_name=None):
    # Overrides the set timezone to UTC - I think...
    tz = timezone.utc if settings.USE_TZ else None

    if not field_name:
        return datetime.datetime.fromtimestamp(response, tz)
    else:
        if field_name in response and response[field_name]:
            return datetime.datetime.fromtimestamp(response[field_name], tz)


class StripeObject(TimeStampedModel):

    stripe_id = models.CharField(max_length=50, unique=True)

    class Meta:
        abstract = True


@python_2_unicode_compatible
class EventProcessingException(TimeStampedModel):

    event = models.ForeignKey("Event", null=True)
    data = models.TextField()
    message = models.CharField(max_length=500)
    traceback = models.TextField()

    @classmethod
    def log(cls, data, exception, event):
        cls.objects.create(
            event=event,
            data=data or "",
            message=str(exception),
            traceback=exception_traceback.format_exc()
        )

    def __str__(self):
        return "<{message}, pk={pk}, Event={event}>".format(message=self.message, pk=self.pk, event=self.event)


@python_2_unicode_compatible
class Event(StripeObject):

    kind = models.CharField(max_length=250)
    livemode = models.BooleanField(default=False)
    customer = models.ForeignKey("Customer", null=True)
    webhook_message = JSONField()
    validated_message = JSONField(null=True)
    valid = models.NullBooleanField(null=True)
    processed = models.BooleanField(default=False)

    @property
    def message(self):
        return self.validated_message

    def __str__(self):
        return "<{kind}, stripe_id={stripe_id}>".format(kind=self.kind, stripe_id=self.stripe_id)

    def link_customer(self):
        stripe_customer_id = None
        stripe_customer_crud_events = [
            "customer.created",
            "customer.updated",
            "customer.deleted"
        ]
        if self.kind in stripe_customer_crud_events:
            stripe_customer_id = self.message["data"]["object"]["id"]
        else:
            stripe_customer_id = self.message["data"]["object"].get("customer", None)

        if stripe_customer_id is not None:
            try:
                self.customer = Customer.objects.get(stripe_id=stripe_customer_id)
                self.save()
            except Customer.DoesNotExist:
                pass

    def validate(self):
        evt = stripe.Event.retrieve(self.stripe_id)
        self.validated_message = json.loads(
            json.dumps(
                evt.to_dict(),
                sort_keys=True,
                cls=stripe.StripeObjectEncoder
            )
        )
        self.valid = self.webhook_message["data"] == self.validated_message["data"]
        self.save()

    def process(self):
        """
            "account.updated",
            "account.application.deauthorized",
            "charge.succeeded",
            "charge.failed",
            "charge.refunded",
            "charge.dispute.created",
            "charge.dispute.updated",
            "charge.dispute.closed",
            "customer.created",
            "customer.updated",
            "customer.deleted",
            "customer.source.created",
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "customer.subscription.trial_will_end",
            "customer.discount.created",
            "customer.discount.updated",
            "customer.discount.deleted",
            "invoice.created",
            "invoice.updated",
            "invoice.payment_succeeded",
            "invoice.payment_failed",
            "invoiceitem.created",
            "invoiceitem.updated",
            "invoiceitem.deleted",
            "plan.created",
            "plan.updated",
            "plan.deleted",
            "coupon.created",
            "coupon.updated",
            "coupon.deleted",
            "transfer.created",
            "transfer.updated",
            "transfer.failed",
            "ping"
        """
        if self.valid and not self.processed:
            try:
                # Link the customer
                if not self.kind.startswith("plan.") and not self.kind.startswith("transfer."):
                    self.link_customer()

                # Handle events
                if self.kind.startswith("invoice."):
                    Invoice.handle_event(self)
                elif self.kind.startswith("charge."):
                    self.customer.record_charge(self.message["data"]["object"]["id"])
                elif self.kind.startswith("transfer."):
                    Transfer.process_transfer(self, self.message["data"]["object"])
                elif self.kind.startswith("customer.subscription."):
                    if self.customer:
                        if Customer.allow_multiple_subscriptions:
                            self.customer.sync_subscriptions()
                        else:
                            if self.kind == "customer.subscription.deleted":
                                self.customer.current_subscription.status = Subscription.STATUS_CANCELLED
                                self.customer.current_subscription.canceled_at = timezone.now()
                                self.customer.current_subscription.save()
                            else:
                                self.customer.sync_current_subscription()
                elif self.kind == "customer.deleted":
                    self.customer.purge()
                self.send_signal()
                self.processed = True
                self.save()
            except stripe.StripeError as exc:
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


class Transfer(StripeObject):
    event = models.ForeignKey(Event, related_name="transfers")
    amount = models.DecimalField(decimal_places=2, max_digits=7)
    status = models.CharField(max_length=25)
    date = models.DateTimeField()
    description = models.TextField(null=True, blank=True)
    adjustment_count = models.IntegerField()
    adjustment_fees = models.DecimalField(decimal_places=2, max_digits=7)
    adjustment_gross = models.DecimalField(decimal_places=2, max_digits=7)
    charge_count = models.IntegerField()
    charge_fees = models.DecimalField(decimal_places=2, max_digits=7)
    charge_gross = models.DecimalField(decimal_places=2, max_digits=7)
    collected_fee_count = models.IntegerField()
    collected_fee_gross = models.DecimalField(decimal_places=2, max_digits=7)
    net = models.DecimalField(decimal_places=2, max_digits=7)
    refund_count = models.IntegerField()
    refund_fees = models.DecimalField(decimal_places=2, max_digits=7)
    refund_gross = models.DecimalField(decimal_places=2, max_digits=7)
    validation_count = models.IntegerField()
    validation_fees = models.DecimalField(decimal_places=2, max_digits=7)

    objects = TransferManager()

    def __str__(self):
        return "<amount={amount}, status={status}, stripe_id={stripe_id}>".format(amount=self.amount, status=self.status, stripe_id=self.stripe_id)

    def update_status(self):
        self.status = stripe.Transfer.retrieve(self.stripe_id).status
        self.save()

    @classmethod
    def process_transfer(cls, event, transfer):
        defaults = {
            "amount": transfer["amount"] / decimal.Decimal("100"),
            "status": transfer["status"],
            "date": convert_tstamp(transfer, "date"),
            "description": transfer.get("description", ""),
            "adjustment_count": transfer["summary"]["adjustment_count"],
            "adjustment_fees": transfer["summary"]["adjustment_fees"],
            "adjustment_gross": transfer["summary"]["adjustment_gross"],
            "charge_count": transfer["summary"]["charge_count"],
            "charge_fees": transfer["summary"]["charge_fees"],
            "charge_gross": transfer["summary"]["charge_gross"],
            "collected_fee_count": transfer["summary"]["collected_fee_count"],
            "collected_fee_gross": transfer["summary"]["collected_fee_gross"],
            "net": transfer["summary"]["net"] / decimal.Decimal("100"),
            "refund_count": transfer["summary"]["refund_count"],
            "refund_fees": transfer["summary"]["refund_fees"],
            "refund_gross": transfer["summary"]["refund_gross"],
            "validation_count": transfer["summary"]["validation_count"],
            "validation_fees": transfer["summary"]["validation_fees"],
        }
        for field in defaults:
            if field.endswith("fees") or field.endswith("gross"):
                defaults[field] = defaults[field] / decimal.Decimal("100")

        if event.kind == "transfer.paid":
            defaults.update({"event": event})
            obj, created = Transfer.objects.get_or_create(
                stripe_id=transfer["id"],
                defaults=defaults
            )
        else:
            obj, created = Transfer.objects.get_or_create(
                stripe_id=transfer["id"],
                event=event,
                defaults=defaults
            )

        if created:
            for fee in transfer["summary"]["charge_fee_details"]:
                obj.charge_fee_details.create(
                    amount=fee["amount"] / decimal.Decimal("100"),
                    application=fee.get("application", ""),
                    description=fee.get("description", ""),
                    kind=fee["type"]
                )
        else:
            obj.status = transfer["status"]
            obj.save()

        if event.kind == "transfer.updated":
            obj.update_status()


class TransferChargeFee(TimeStampedModel):
    transfer = models.ForeignKey(Transfer, related_name="charge_fee_details")
    amount = models.DecimalField(decimal_places=2, max_digits=7)
    application = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    kind = models.CharField(max_length=150)


@python_2_unicode_compatible
class Customer(StripeObject):
    subscriber = models.OneToOneField(getattr(settings, 'DJSTRIPE_SUBSCRIBER_MODEL', settings.AUTH_USER_MODEL), null=True)
    card_fingerprint = models.CharField(max_length=200, blank=True)
    card_last_4 = models.CharField(max_length=4, blank=True)
    card_kind = models.CharField(max_length=50, blank=True)
    card_exp_month = models.PositiveIntegerField(blank=True, null=True)
    card_exp_year = models.PositiveIntegerField(blank=True, null=True)
    date_purged = models.DateTimeField(null=True, editable=False)

    objects = CustomerManager()

    allow_multiple_subscriptions = djstripe_settings.ALLOW_MULTIPLE_SUBSCRIPTIONS
    retain_canceled_subscriptions = djstripe_settings.RETAIN_CANCELED_SUBSCRIPTIONS

    def __str__(self):
        return "<{subscriber}, stripe_id={stripe_id}>".format(subscriber=smart_text(self.subscriber), stripe_id=self.stripe_id)

    @property
    def stripe_customer(self):
        return stripe.Customer.retrieve(self.stripe_id)

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
        self.card_fingerprint = ""
        self.card_last_4 = ""
        self.card_kind = ""
        self.card_exp_month = None
        self.card_exp_year = None
        self.date_purged = timezone.now()
        self.save()

    def delete(self, using=None):
        # Only way to delete a customer is to use SQL
        self.purge()

    def can_charge(self):
        return self.card_fingerprint and \
            self.card_last_4 and \
            self.card_kind and \
            self.date_purged is None

    def has_active_subscription(self):
        for subscription in self.subscriptions.all():
            if subscription.is_valid():
                return True
        return False

    @property
    def current_subscription(self):
        if Customer.allow_multiple_subscriptions:
            raise SubscriptionApiError(
                "current_subscription not available with multiple subscriptions"
            )
        if self.subscriptions.count():
            return self.subscriptions.all()[0]
        else:
            raise Subscription.DoesNotExist

    def matching_stripe_subscription(self, subscription, cu=None):
        """
        Look up the Stripe subscription matching this subscription, using the
        Stripe ID. If multiple subscriptions are not allowed, the subscription
        parameter is ignored, and we just return the first (and presumably only)
        Stripe subscription.
        """
        cu = cu or self.stripe_customer
        stripe_subscription = None
        if cu.subscriptions.count > 0:
            if not Customer.allow_multiple_subscriptions:
                stripe_subscription = cu.subscriptions.data[0]
            else:
                if subscription:
                    matching = [sub for sub in cu.subscriptions.data if sub.id == subscription.stripe_id]
                    if matching:
                        stripe_subscription = matching[0]
        return stripe_subscription

    def cancel_subscription(self, at_period_end=True, subscription=None):
        if Customer.allow_multiple_subscriptions and not subscription:
            raise SubscriptionApiError(
                "Must specify a subscription to cancel"
            )
        if not subscription:
            if self.subscriptions.count() == 0:
                raise SubscriptionCancellationFailure(
                    "Customer does not have current subscription"
                )
            subscription = self.subscriptions.all()[0]

        """
        If plan has trial days and customer cancels before trial period ends,
        then end subscription now, i.e. at_period_end=False
        """
        if subscription.trial_end and subscription.trial_end > timezone.now():
            at_period_end = False
        cu = self.stripe_customer
        stripe_subscription = None
        if cu.subscriptions.count > 0:
            if Customer.allow_multiple_subscriptions:
                matching = [sub for sub in cu.subscriptions.data if sub.id == subscription.stripe_id]
                if matching:
                    stripe_subscription = matching[0]
            else:
                stripe_subscription = cu.subscriptions.data[0]
        if stripe_subscription:
            stripe_subscription = stripe_subscription.delete(at_period_end=at_period_end)
            subscription.status = stripe_subscription.status
            subscription.cancel_at_period_end = stripe_subscription.cancel_at_period_end
            subscription.current_period_end = convert_tstamp(stripe_subscription, "current_period_end")
            subscription.canceled_at = convert_tstamp(stripe_subscription, "canceled_at") or timezone.now()
            if not at_period_end:
                subscription.ended_at = subscription.canceled_at
            subscription.save()
            cancelled.send(sender=self, stripe_response=stripe_subscription)
        else:
            """
            No Stripe subscription exists, perhaps because it was independently cancelled at Stripe.
            Synthesise the cancellation state using the current time.
            """
            subscription.status = Subscription.STATUS_CANCELLED
            subscription.canceled_at = timezone.now()
            if not at_period_end:
                subscription.ended_at = subscription.canceled_at
            subscription.save()

        return subscription

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

        stripe_customer = stripe.Customer.create(email=subscriber.email)
        cus = Customer.objects.create(subscriber=subscriber, stripe_id=stripe_customer.id)

        if djstripe_settings.DEFAULT_PLAN and trial_days:
            cus.subscribe(plan=djstripe_settings.DEFAULT_PLAN, trial_days=trial_days)

        return cus

    def update_card(self, token):
        cu = self.stripe_customer
        cu.card = token
        cu.save()
        self.card_fingerprint = cu.active_card.fingerprint
        self.card_last_4 = cu.active_card.last4
        self.card_kind = cu.active_card.type
        self.card_exp_month = cu.active_card.exp_month
        self.card_exp_year = cu.active_card.exp_year
        self.save()
        card_changed.send(sender=self, stripe_response=cu)

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
            invoice = stripe.Invoice.create(customer=self.stripe_id)
            invoice.pay()
            return True
        except stripe.InvalidRequestError:
            return False  # There was nothing to invoice

    def sync(self, cu=None):
        cu = cu or self.stripe_customer
        if cu.active_card:
            self.card_fingerprint = cu.active_card.fingerprint
            self.card_last_4 = cu.active_card.last4
            self.card_kind = cu.active_card.type
            self.card_exp_month = cu.active_card.exp_month
            self.card_exp_year = cu.active_card.exp_year
            self.save()

    def sync_invoices(self, cu=None, **kwargs):
        cu = cu or self.stripe_customer
        for invoice in cu.invoices(**kwargs).data:
            Invoice.sync_from_stripe_data(invoice, send_receipt=False)

    def sync_charges(self, cu=None, **kwargs):
        cu = cu or self.stripe_customer
        for charge in cu.charges(**kwargs).data:
            self.record_charge(charge.id)

    def sync_subscriptions(self, cu=None):
        """
        Remove all existing Subscription records and regenerate from the Stripe
        subscriptions.
        """
        cu = cu or self.stripe_customer
        stripe_subscriptions = cu.subscriptions
        if Customer.allow_multiple_subscriptions and not Customer.retain_canceled_subscriptions:
            self.subscriptions.all().delete()
        first_sub = None
        if stripe_subscriptions.count > 0:
            for stripe_subscription in stripe_subscriptions.data:
                try:
                    if Customer.allow_multiple_subscriptions:
                        subscription = self.subscriptions.get(stripe_id=stripe_subscription.id)
                    else:
                        if self.subscriptions.count() == 0:
                            raise Subscription.DoesNotExist
                        subscription = self.subscriptions.all()[0]
                    subscription.plan = djstripe_settings.plan_from_stripe_id(stripe_subscription.plan.id)
                    subscription.current_period_start = convert_tstamp(
                        stripe_subscription.current_period_start
                    )
                    subscription.current_period_end = convert_tstamp(
                        stripe_subscription.current_period_end
                    )
                    subscription.amount = (stripe_subscription.plan.amount / decimal.Decimal("100"))
                    subscription.status = stripe_subscription.status
                    subscription.cancel_at_period_end = stripe_subscription.cancel_at_period_end
                    subscription.canceled_at = convert_tstamp(stripe_subscription, "canceled_at")
                    subscription.quantity = stripe_subscription.quantity
                    subscription.start = convert_tstamp(stripe_subscription.start)
                    # ended_at will generally be null, since Stripe does not retain ended subscriptions.
                    subscription.ended_at = convert_tstamp(stripe_subscription, "ended_at")

                    if stripe_subscription.trial_start and stripe_subscription.trial_end:
                        subscription.trial_start = convert_tstamp(stripe_subscription.trial_start)
                        subscription.trial_end = convert_tstamp(stripe_subscription.trial_end)
                    else:
                        """
                        Avoids keeping old values for trial_start and trial_end
                        for cases where customer had a subscription with trial days
                        then one without that (s)he cancels.
                        """
                        subscription.trial_start = None
                        subscription.trial_end = None

                except Subscription.DoesNotExist:
                    subscription = Subscription(
                        stripe_id=stripe_subscription.id,
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
                        quantity=stripe_subscription.quantity,
                        ended_at=convert_tstamp(stripe_subscription, "ended_at"),
                        trial_end=convert_tstamp(stripe_subscription, "trial_end"),
                        trial_start=convert_tstamp(stripe_subscription, "trial_start"),
                    )

                subscription.save()
                if not first_sub:
                    first_sub = subscription

                if not Customer.allow_multiple_subscriptions:
                    break

        return first_sub

    def sync_current_subscription(self, cu=None):
        """
        Synchronise with Stripe when only using a single subscription.
        """
        if Customer.allow_multiple_subscriptions:
            raise SubscriptionApiError(
                "sync_current_subscription not available with multiple subscriptions"
            )
        cu = cu or self.stripe_customer
        data = cu.subscriptions.data
        sub = data[0] if data else None
        if sub:
            return self.sync_subscriptions()

    def update_plan_quantity(self, quantity, charge_immediately=False, subscription=None):
        if Customer.allow_multiple_subscriptions and not subscription:
            raise SubscriptionApiError("Must specify a subscription to update")
        stripe_subscription = self.matching_stripe_subscription(subscription)
        if stripe_subscription:
            self.subscribe(
                plan=djstripe_settings.plan_from_stripe_id(stripe_subscription.plan.id),
                quantity=quantity,
                charge_immediately=charge_immediately,
                subscription=subscription
            )

    def subscribe(self, plan, quantity=1, trial_days=None,
                  charge_immediately=True, prorate=djstripe_settings.PRORATION_POLICY,
                  subscription=None):
        """
        Retrieve the first (and only) Stripe subscription if it exists, and if multiple
        subscriptions are not allowed. For multiple subscriptions, create a new
        subscription, unless the subscription parameter is provided, in which that
        subscription will be modified (upgraded).
        """
        cu = self.stripe_customer
        stripe_subscription = self.matching_stripe_subscription(subscription, cu)
        """
        Trial_days corresponds to the value specified by the selected plan
        for the key trial_period_days.
        """
        if ("trial_period_days" in djstripe_settings.PAYMENTS_PLANS[plan]):
            trial_days = djstripe_settings.PAYMENTS_PLANS[plan]["trial_period_days"]
        if stripe_subscription:
            stripe_subscription.plan = djstripe_settings.PAYMENTS_PLANS[plan]["stripe_plan_id"]
            stripe_subscription.prorate = prorate
            stripe_subscription.quantity = quantity
            if trial_days:
                stripe_subscription.trial_end = timezone.now() + datetime.timedelta(days=trial_days)
            response = stripe_subscription.save()
        else:
            response = cu.subscriptions.create(
                plan=djstripe_settings.PAYMENTS_PLANS[plan]["stripe_plan_id"],
                trial_end=timezone.now() + datetime.timedelta(days=trial_days) if trial_days else None,
                prorate=prorate,
                quantity=quantity
            )
        if Customer.allow_multiple_subscriptions:
            self.sync_subscriptions()
        else:
            self.sync_current_subscription()
        if charge_immediately:
            self.send_invoice()
        subscription_made.send(sender=self, plan=plan, stripe_response=response)

    def charge(self, amount, currency="usd", description=None, send_receipt=True, **kwargs):
        """
        This method expects `amount` to be a Decimal type representing a
        dollar amount. It will be converted to cents so any decimals beyond
        two will be ignored.
        """
        if not isinstance(amount, decimal.Decimal):
            raise ValueError(
                "You must supply a decimal value representing dollars."
            )
        resp = stripe.Charge.create(
            amount=int(amount * 100),  # Convert dollars into cents
            currency=currency,
            customer=self.stripe_id,
            description=description,
            **kwargs
        )
        obj = self.record_charge(resp["id"])
        if send_receipt:
            obj.send_receipt()
        return obj

    def add_invoice_item(self, amount, currency="usd", invoice_id=None, description=None):
        """
        Adds an arbitrary charge or credit to the customer's upcoming invoice.
        Different than creating a charge. Charges are separate bills that get
        processed immediately. Invoice items are appended to the customer's next
        invoice. This is extremely useful when adding surcharges to subscriptions.

        This method expects `amount` to be a Decimal type representing a
        dollar amount. It will be converted to cents so any decimals beyond
        two will be ignored.

        Note: Since invoice items are appended to invoices, a record will be stored
        in dj-stripe when invoices are pulled.

        :param invoice:
            The ID of an existing invoice to add this invoice item to.
            When left blank, the invoice item will be added to the next upcoming
            scheduled invoice. Use this when adding invoice items in response
            to an invoice.created webhook. You cannot add an invoice item to
            an invoice that has already been paid, attempted or closed.
        """

        if not isinstance(amount, decimal.Decimal):
            raise ValueError(
                "You must supply a decimal value representing dollars."
            )
        stripe.InvoiceItem.create(
            amount=int(amount * 100),  # Convert dollars into cents
            currency=currency,
            customer=self.stripe_id,
            description=description,
            invoice=invoice_id,
        )

    def record_charge(self, charge_id):
        data = stripe.Charge.retrieve(charge_id)
        return Charge.sync_from_stripe_data(data)


class Subscription(StripeObject):
    STATUS_TRIALING = "trialing"
    STATUS_ACTIVE = "active"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELLED = "canceled"
    STATUS_UNPAID = "unpaid"

    customer = models.ForeignKey(
        Customer,
        related_name="subscriptions",
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


class Invoice(StripeObject):
    customer = models.ForeignKey(Customer, related_name="invoices")
    attempted = models.NullBooleanField()
    attempts = models.PositiveIntegerField(null=True)
    closed = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    period_end = models.DateTimeField()
    period_start = models.DateTimeField()
    subtotal = models.DecimalField(decimal_places=2, max_digits=7)
    total = models.DecimalField(decimal_places=2, max_digits=7)
    date = models.DateTimeField()
    charge = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return "<total={total}, paid={paid}, stripe_id={stripe_id}>".format(total=self.total, paid=smart_text(self.paid), stripe_id=self.stripe_id)

    def retry(self):
        if not self.paid and not self.closed:
            inv = stripe.Invoice.retrieve(self.stripe_id)
            inv.pay()
            return True
        return False

    def status(self):
        if self.paid:
            return "Paid"
        if self.closed:
            return "Closed"
        return "Open"

    @classmethod
    def sync_from_stripe_data(cls, stripe_invoice, send_receipt=True):
        c = Customer.objects.get(stripe_id=stripe_invoice["customer"])
        period_end = convert_tstamp(stripe_invoice, "period_end")
        period_start = convert_tstamp(stripe_invoice, "period_start")
        date = convert_tstamp(stripe_invoice, "date")

        invoice, created = cls.objects.get_or_create(
            stripe_id=stripe_invoice["id"],
            defaults=dict(
                customer=c,
                attempted=stripe_invoice["attempted"],
                closed=stripe_invoice["closed"],
                paid=stripe_invoice["paid"],
                period_end=period_end,
                period_start=period_start,
                subtotal=stripe_invoice["subtotal"] / decimal.Decimal("100"),
                total=stripe_invoice["total"] / decimal.Decimal("100"),
                date=date,
                charge=stripe_invoice.get("charge") or ""
            )
        )
        if not created:
            invoice.attempted = stripe_invoice["attempted"]
            invoice.closed = stripe_invoice["closed"]
            invoice.paid = stripe_invoice["paid"]
            invoice.period_end = period_end
            invoice.period_start = period_start
            invoice.subtotal = stripe_invoice["subtotal"] / decimal.Decimal("100")
            invoice.total = stripe_invoice["total"] / decimal.Decimal("100")
            invoice.date = date
            invoice.charge = stripe_invoice.get("charge") or ""
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
            obj = c.record_charge(stripe_invoice["charge"])
            obj.invoice = invoice
            obj.save()
            if send_receipt:
                obj.send_receipt()
        return invoice

    @classmethod
    def handle_event(cls, event):
        valid_events = ["invoice.payment_failed", "invoice.payment_succeeded", "invoice.created", ]
        if event.kind in valid_events:
            invoice_data = event.message["data"]["object"]
            stripe_invoice = stripe.Invoice.retrieve(invoice_data["id"])
            cls.sync_from_stripe_data(stripe_invoice, send_receipt=djstripe_settings.SEND_INVOICE_RECEIPT_EMAILS)


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


class Charge(StripeObject):
    customer = models.ForeignKey(Customer, related_name="charges")
    invoice = models.ForeignKey(Invoice, null=True, related_name="charges")
    card_last_4 = models.CharField(max_length=4, blank=True)
    card_kind = models.CharField(max_length=50, blank=True)
    amount = models.DecimalField(decimal_places=2, max_digits=7, null=True)
    amount_refunded = models.DecimalField(decimal_places=2, max_digits=7, null=True)
    description = models.TextField(blank=True)
    paid = models.NullBooleanField(null=True)
    disputed = models.NullBooleanField(null=True)
    refunded = models.NullBooleanField(null=True)
    captured = models.NullBooleanField(null=True)
    fee = models.DecimalField(decimal_places=2, max_digits=7, null=True)
    receipt_sent = models.BooleanField(default=False)
    charge_created = models.DateTimeField(null=True, blank=True)

    objects = ChargeManager()

    def __str__(self):
        return "<amount={amount}, paid={paid}, stripe_id={stripe_id}>".format(amount=self.amount, paid=smart_text(self.paid), stripe_id=self.stripe_id)

    def calculate_refund_amount(self, amount=None):
        eligible_to_refund = self.amount - (self.amount_refunded or 0)
        if amount:
            amount_to_refund = min(eligible_to_refund, amount)
        else:
            amount_to_refund = eligible_to_refund
        return int(amount_to_refund * 100)

    def refund(self, amount=None):
        charge_obj = stripe.Charge.retrieve(self.stripe_id).refund(
            amount=self.calculate_refund_amount(amount=amount)
        )
        return Charge.sync_from_stripe_data(charge_obj)

    def capture(self):
        """
        Capture the payment of an existing, uncaptured, charge. This is the second half of the two-step payment flow,
        where first you created a charge with the capture option set to false.
        See https://stripe.com/docs/api#capture_charge
        """
        charge_obj = stripe.Charge.retrieve(self.stripe_id).capture()
        return Charge.sync_from_stripe_data(charge_obj)

    @classmethod
    def sync_from_stripe_data(cls, data):
        customer = Customer.objects.get(stripe_id=data["customer"])
        obj, _ = customer.charges.get_or_create(stripe_id=data["id"])
        invoice_id = data.get("invoice", None)
        if obj.customer.invoices.filter(stripe_id=invoice_id).exists():
            obj.invoice = obj.customer.invoices.get(stripe_id=invoice_id)
        obj.card_last_4 = data["card"]["last4"]
        obj.card_kind = data["card"]["type"]
        obj.amount = (data["amount"] / decimal.Decimal("100"))
        obj.paid = data["paid"]
        obj.refunded = data["refunded"]
        obj.captured = data["captured"]
        obj.fee = (data["fee"] / decimal.Decimal("100"))
        obj.disputed = data["dispute"] is not None
        obj.charge_created = convert_tstamp(data, "created")
        if data.get("description"):
            obj.description = data["description"]
        if data.get("amount_refunded"):
            obj.amount_refunded = (data["amount_refunded"] / decimal.Decimal("100"))
        if data["refunded"]:
            obj.amount_refunded = (data["amount"] / decimal.Decimal("100"))
        obj.save()
        return obj

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


@python_2_unicode_compatible
class Plan(StripeObject):
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

    def __str__(self):
        return "<{name}, stripe_id={stripe_id}>".format(name=smart_text(self.name), stripe_id=self.stripe_id)

    @classmethod
    def create(cls, metadata={}, **kwargs):
        """Create and then return a Plan (both in Stripe, and in our db)."""

        stripe.Plan.create(
            id=kwargs['stripe_id'],
            amount=int(kwargs['amount'] * 100),
            currency=kwargs['currency'],
            interval=kwargs['interval'],
            interval_count=kwargs.get('interval_count', None),
            name=kwargs['name'],
            trial_period_days=kwargs.get('trial_period_days'),
            metadata=metadata)

        plan = Plan.objects.create(
            stripe_id=kwargs['stripe_id'],
            amount=kwargs['amount'],
            currency=kwargs['currency'],
            interval=kwargs['interval'],
            interval_count=kwargs.get('interval_count', None),
            name=kwargs['name'],
            trial_period_days=kwargs.get('trial_period_days'),
        )

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

        p = stripe.Plan.retrieve(self.stripe_id)
        p.name = self.name
        p.save()

        self.save()

    @property
    def stripe_plan(self):
        """Return the plan data from Stripe."""
        return stripe.Plan.retrieve(self.stripe_id)
