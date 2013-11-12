"""
Beging porting from django-stripe-payments
"""
from __future__ import unicode_literals
import datetime
import decimal
import json
import traceback

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import models
from django.utils import timezone
from django.template.loader import render_to_string

from django.contrib.sites.models import Site

from jsonfield.fields import JSONField
from model_utils.models import TimeStampedModel
import stripe

from . import exceptions
from .managers import CustomerManager, ChargeManager, TransferManager
from .settings import PAYMENTS_PLANS, INVOICE_FROM_EMAIL
from .settings import plan_from_stripe_id
from .signals import WEBHOOK_SIGNALS
from .signals import subscription_made, cancelled, card_changed
from .signals import webhook_processing_error
from .settings import TRIAL_PERIOD_FOR_USER_CALLBACK
from .settings import DEFAULT_PLAN


stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = getattr(settings, "STRIPE_API_VERSION", "2012-11-07")


def convert_tstamp(response, field_name=None):
    try:
        if field_name and response[field_name]:
            if settings.USE_TZ:
                return datetime.datetime.fromtimestamp(
                    response[field_name],
                    timezone.utc
                )
            else:
                return datetime.datetime.fromtimestamp(response[field_name])
        if not field_name:
            if settings.USE_TZ:
                return datetime.datetime.fromtimestamp(
                    response,
                    timezone.utc
                )
            else:
                return datetime.datetime.fromtimestamp(response)
    except KeyError:
        pass
    return None


class StripeObject(TimeStampedModel):

    stripe_id = models.CharField(max_length=50, unique=True)

    class Meta:
        abstract = True


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
            traceback=traceback.format_exc()
        )

    def __unicode__(self):
        return u"<%s, pk=%s, Event=%s>" % (self.message, self.pk, self.event)


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

    def __unicode__(self):
        return "%s - %s" % (self.kind, self.stripe_id)

    def link_customer(self):
        cus_id = None
        customer_crud_events = [
            "customer.created",
            "customer.updated",
            "customer.deleted"
        ]
        if self.kind in customer_crud_events:
            cus_id = self.message["data"]["object"]["id"]
        else:
            cus_id = self.message["data"]["object"].get("customer", None)

        if cus_id is not None:
            try:
                self.customer = Customer.objects.get(stripe_id=cus_id)
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
        if self.webhook_message["data"] == self.validated_message["data"]:
            self.valid = True
        else:
            self.valid = False
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
            "chagne.dispute.closed",
            "customer.created",
            "customer.updated",
            "customer.deleted",
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
                if not self.kind.startswith("plan.") and \
                        not self.kind.startswith("transfer."):
                    self.link_customer()
                if self.kind.startswith("invoice."):
                    Invoice.handle_event(self)
                elif self.kind.startswith("charge."):
                    if not self.customer:
                        self.link_customer()
                    self.customer.record_charge(
                        self.message["data"]["object"]["id"]
                    )
                elif self.kind.startswith("transfer."):
                    Transfer.process_transfer(
                        self,
                        self.message["data"]["object"]
                    )
                elif self.kind.startswith("customer.subscription."):
                    if not self.customer:
                        self.link_customer()
                    if self.customer:
                        self.customer.sync_current_subscription()
                elif self.kind == "customer.deleted":
                    if not self.customer:
                        self.link_customer()
                    self.customer.purge()
                self.send_signal()
                self.processed = True
                self.save()
            except stripe.StripeError as e:
                EventProcessingException.log(
                    data=e.http_body,
                    exception=e,
                    event=self
                )
                webhook_processing_error.send(
                    sender=Event,
                    data=e.http_body,
                    exception=e
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


class Customer(StripeObject):

    user = models.OneToOneField(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), null=True)
    card_fingerprint = models.CharField(max_length=200, blank=True)
    card_last_4 = models.CharField(max_length=4, blank=True)
    card_kind = models.CharField(max_length=50, blank=True)
    date_purged = models.DateTimeField(null=True, editable=False)

    objects = CustomerManager()

    def __unicode__(self):
        return unicode(self.user)

    @property
    def stripe_customer(self):
        return stripe.Customer.retrieve(self.stripe_id)

    def purge(self):
        try:
            self.stripe_customer.delete()
        except stripe.InvalidRequestError as e:
            if e.message.startswith("No such customer:"):
                # The exception was thrown because the customer was already
                # deleted on the stripe side, ignore the exception
                pass
            else:
                # The exception was raised for another reason, re-raise it
                raise
        self.user = None
        self.card_fingerprint = ""
        self.card_last_4 = ""
        self.card_kind = ""
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
        try:
            return self.current_subscription.is_valid()
        except CurrentSubscription.DoesNotExist:
            return False

    def cancel_subscription(self, at_period_end=True):
        try:
            current_subscription = self.current_subscription
        except CurrentSubscription.DoesNotExist:
            raise exceptions.SubscriptionCancellationFailure(
                "Customer does not have current subscription"
            )
        try:
            sub = self.stripe_customer.cancel_subscription(at_period_end=at_period_end)
        except stripe.InvalidRequestError as e:
            raise exceptions.SubscriptionCancellationFailure(
                "Customer's information is not current with Stripe.\n{}".format(
                    e.message
                )
            )
        current_subscription.status = sub.status
        current_subscription.cancel_at_period_end = sub.cancel_at_period_end
        current_subscription.period_end = convert_tstamp(sub, "current_period_end")
        current_subscription.save()
        cancelled.send(sender=self, stripe_response=sub)
        return current_subscription

    def cancel(self, at_period_end=True):
        """ Utility method to preserve usage of previous API """
        return self.cancel_subscription(at_period_end=at_period_end)

    @classmethod
    def get_or_create(cls, user):
        try:
            return Customer.objects.get(user=user), False
        except Customer.DoesNotExist:
            return cls.create(user), True

    @classmethod
    def create(cls, user):

        trial_days = None
        if TRIAL_PERIOD_FOR_USER_CALLBACK:
            trial_days = TRIAL_PERIOD_FOR_USER_CALLBACK(user)

        stripe_customer = stripe.Customer.create(
            email=user.email
        )
        cus = Customer.objects.create(
            user=user,
            stripe_id=stripe_customer.id
        )

        if DEFAULT_PLAN and trial_days:
            cus.subscribe(plan=DEFAULT_PLAN, trial_days=trial_days)

        return cus

    def update_card(self, token):
        cu = self.stripe_customer
        cu.card = token
        cu.save()
        self.card_fingerprint = cu.active_card.fingerprint
        self.card_last_4 = cu.active_card.last4
        self.card_kind = cu.active_card.type
        self.save()
        card_changed.send(sender=self, stripe_response=cu)

    def retry_unpaid_invoices(self):
        self.sync_invoices()
        for inv in self.invoices.filter(paid=False, closed=False):
            try:
                inv.retry()  # Always retry unpaid invoices
            except stripe.InvalidRequestError as error:
                if error.message != "Invoice is already paid":
                    raise error

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
            self.save()

    def sync_invoices(self, cu=None, **kwargs):
        cu = cu or self.stripe_customer
        for invoice in cu.invoices(**kwargs).data:
            Invoice.sync_from_stripe_data(invoice, send_receipt=False)

    def sync_charges(self, cu=None, **kwargs):
        cu = cu or self.stripe_customer
        for charge in cu.charges(**kwargs).data:
            self.record_charge(charge.id)

    def sync_current_subscription(self, cu=None):
        cu = cu or self.stripe_customer
        sub = cu.subscription
        if sub:
            try:
                sub_obj = self.current_subscription
                sub_obj.plan = plan_from_stripe_id(sub.plan.id)
                sub_obj.current_period_start = convert_tstamp(
                    sub.current_period_start
                )
                sub_obj.current_period_end = convert_tstamp(
                    sub.current_period_end
                )
                sub_obj.amount = (sub.plan.amount / decimal.Decimal("100"))
                sub_obj.status = sub.status
                sub_obj.cancel_at_period_end = sub.cancel_at_period_end
                sub_obj.start = convert_tstamp(sub.start)
                sub_obj.quantity = sub.quantity
                sub_obj.save()
            except CurrentSubscription.DoesNotExist:
                sub_obj = CurrentSubscription.objects.create(
                    customer=self,
                    plan=plan_from_stripe_id(sub.plan.id),
                    current_period_start=convert_tstamp(
                        sub.current_period_start
                    ),
                    current_period_end=convert_tstamp(
                        sub.current_period_end
                    ),
                    amount=(sub.plan.amount / decimal.Decimal("100")),
                    status=sub.status,
                    cancel_at_period_end=sub.cancel_at_period_end,
                    start=convert_tstamp(sub.start),
                    quantity=sub.quantity
                )

            if sub.trial_start and sub.trial_end:
                sub_obj.trial_start = convert_tstamp(sub.trial_start)
                sub_obj.trial_end = convert_tstamp(sub.trial_end)
                sub_obj.save()

            return sub_obj

    def update_plan_quantity(self, quantity, charge_immediately=False):
        self.subscribe(
            plan=plan_from_stripe_id(
                self.stripe_customer.subscription.plan.id
            ),
            quantity=quantity,
            charge_immediately=charge_immediately
        )

    def subscribe(self, plan, quantity=1, trial_days=None,
                  charge_immediately=True):
        cu = self.stripe_customer
        if trial_days:
            resp = cu.update_subscription(
                plan=PAYMENTS_PLANS[plan]["stripe_plan_id"],
                trial_end=timezone.now() + datetime.timedelta(days=trial_days),
                quantity=quantity
            )
        else:
            resp = cu.update_subscription(
                plan=PAYMENTS_PLANS[plan]["stripe_plan_id"],
                quantity=quantity
            )
        self.sync_current_subscription()
        if charge_immediately:
            self.send_invoice()
        subscription_made.send(sender=self, plan=plan, stripe_response=resp)

    def charge(self, amount, currency="usd", description=None, send_receipt=True):
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
        )
        obj = self.record_charge(resp["id"])
        if send_receipt:
            obj.send_receipt()
        return obj

    def record_charge(self, charge_id):
        data = stripe.Charge.retrieve(charge_id)
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
        return PAYMENTS_PLANS[self.plan]["name"]

    def status_display(self):
        return self.status.replace("_", " ").title()

    def is_period_current(self):
        if self.current_period_end is None:
            return False
        return self.current_period_end > timezone.now()

    def is_status_current(self):
        return self.status in [self.STATUS_TRIALING, self.STATUS_ACTIVE]

    def is_valid(self):
        if not self.is_status_current():
            return False

        if self.cancel_at_period_end and not self.is_period_current():
            return False

        return True


class Invoice(TimeStampedModel):

    stripe_id = models.CharField(max_length=50)
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
            # pylint: disable=C0301
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

            if item.get("plan"):
                plan = plan_from_stripe_id(item["plan"]["id"])
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

        if stripe_invoice.get("charge"):
            obj = c.record_charge(stripe_invoice["charge"])
            obj.invoice = invoice
            obj.save()
            if send_receipt:
                obj.send_receipt()
        return invoice

    @classmethod
    def handle_event(cls, event):
        valid_events = ["invoice.payment_failed", "invoice.payment_succeeded"]
        if event.kind in valid_events:
            invoice_data = event.message["data"]["object"]
            stripe_invoice = stripe.Invoice.retrieve(invoice_data["id"])
            cls.sync_from_stripe_data(stripe_invoice)


class InvoiceItem(TimeStampedModel):
    """ Not inherited from StripeObject because there can be multiple invoice
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
    plan = models.CharField(max_length=100, blank=True)
    quantity = models.IntegerField(null=True)

    def plan_display(self):
        return PAYMENTS_PLANS[self.plan]["name"]


class Charge(StripeObject):

    customer = models.ForeignKey(Customer, related_name="charges")
    invoice = models.ForeignKey(Invoice, null=True, related_name="charges")
    card_last_4 = models.CharField(max_length=4, blank=True)
    card_kind = models.CharField(max_length=50, blank=True)
    amount = models.DecimalField(decimal_places=2, max_digits=7, null=True)
    amount_refunded = models.DecimalField(
        decimal_places=2,
        max_digits=7,
        null=True
    )
    description = models.TextField(blank=True)
    paid = models.NullBooleanField(null=True)
    disputed = models.NullBooleanField(null=True)
    refunded = models.NullBooleanField(null=True)
    fee = models.DecimalField(decimal_places=2, max_digits=7, null=True)
    receipt_sent = models.BooleanField(default=False)
    charge_created = models.DateTimeField(null=True, blank=True)

    objects = ChargeManager()

    def calculate_refund_amount(self, amount=None):
        eligible_to_refund = self.amount - (self.amount_refunded or 0)
        if amount:
            amount_to_refund = min(eligible_to_refund, amount)
        else:
            amount_to_refund = eligible_to_refund
        return int(amount_to_refund * 100)

    def refund(self, amount=None):
        charge_obj = stripe.Charge.retrieve(
            self.stripe_id
        ).refund(
            amount=self.calculate_refund_amount(amount=amount)
        )
        Charge.sync_from_stripe_data(charge_obj)

    @classmethod
    def sync_from_stripe_data(cls, data):
        customer = Customer.objects.get(stripe_id=data["customer"])
        obj, _ = customer.charges.get_or_create(
            stripe_id=data["id"]
        )
        invoice_id = data.get("invoice", None)
        if obj.customer.invoices.filter(stripe_id=invoice_id).exists():
            obj.invoice = obj.customer.invoices.get(stripe_id=invoice_id)
        obj.card_last_4 = data["card"]["last4"]
        obj.card_kind = data["card"]["type"]
        obj.amount = (data["amount"] / decimal.Decimal("100"))
        obj.paid = data["paid"]
        obj.refunded = data["refunded"]
        obj.fee = (data["fee"] / decimal.Decimal("100"))
        obj.disputed = data["dispute"] is not None
        obj.charge_created = convert_tstamp(data, "created")
        if data.get("description"):
            obj.description = data["description"]
        if data.get("amount_refunded"):
            # pylint: disable=C0301
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
                to=[self.customer.user.email],
                from_email=INVOICE_FROM_EMAIL
            ).send()
            self.receipt_sent = num_sent > 0
            self.save()
