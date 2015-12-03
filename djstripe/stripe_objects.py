# -*- coding: utf-8 -*-
"""
.. module:: djstripe.stripe_objects
   :synopsis: dj-stripe - Abstract model definitions to provide our view of Stripe's objects

.. moduleauthor:: Bill Huneke (@wahuneke)

This module is an effort to isolate (as much as possible) the API dependent code in one
place. Primarily this is:

1) create models containing the fields that we care about, mapping to Stripe's fields
2) create methods for consistently syncing our database with Stripe's version of the objects
3) centralized routines for creating new database records to match incoming Stripe objects

This module defines abstract models which are then extended in models.py to provide the remaining
dj-stripe functionality.
"""

from contextlib import contextmanager
import datetime
import decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible, smart_text
from jsonfield import JSONField

from model_utils.models import TimeStampedModel
import stripe

from .managers import TransferManager, StripeObjectManager


stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = getattr(settings, "STRIPE_API_VERSION", "2012-11-07")


@contextmanager
def stripe_temporary_api_key(temp_key):
    """
    A contextmanager

    Temporarily replace the global api_key used in stripe API calls with the given value
    the original value is restored as soon as context exits
    """
    import stripe
    backup_key = stripe.api_key
    stripe.api_key = temp_key
    yield
    stripe.api_key = backup_key


def convert_tstamp(response, field_name=None):
    # Overrides the set timezone to UTC - I think...
    tz = timezone.utc if settings.USE_TZ else None

    if not field_name:
        return datetime.datetime.fromtimestamp(response, tz)
    else:
        if field_name in response and response[field_name]:
            return datetime.datetime.fromtimestamp(response[field_name], tz)


@python_2_unicode_compatible
class StripeObject(TimeStampedModel):
    # This must be defined in descendants of this model/mixin
    # e.g. "Event", "Charge", "Customer", etc.
    stripe_api_name = None
    objects = models.Manager()
    stripe_objects = StripeObjectManager()

    class Meta:
        abstract = True

    stripe_id = models.CharField(max_length=50, unique=True)
    # livemode = models.BooleanField(default=False)

    @classmethod
    def api(cls):
        """
        Get the api object for this type of stripe object (requires
        stripe_api_name attribute to be set on model).
        """
        if cls.stripe_api_name is None:
            raise NotImplementedError("StripeObject descendants are required to define "
                                      "the stripe_api_name attribute")
        # e.g. stripe.Event, stripe.Charge, etc
        return getattr(stripe, cls.stripe_api_name)

    def api_retrieve(self):
        """
        Implement very commonly used API function 'retrieve'
        """
        # Run stripe.X.retreive(id)
        return type(self).api().retrieve(self.stripe_id)

    @classmethod
    def api_create(cls, **kwargs):
        """
        Call the stripe API's create operation for this model
        """
        return cls.api().create(**kwargs)

    def str_parts(self):
        """
        Extend this to add information to the string representation of the object

        :rtype: list of str
        """
        return ["stripe_id={id}".format(id=self.stripe_id)]

    @classmethod
    def stripe_object_to_record(cls, data):
        """
        This takes an object, as it is formatted in Stripe's current API for our object
        type. In return, it provides a dict. The dict can be used to create a record or
        to update a record

        This function takes care of mapping from one field name to another, converting
        from cents to dollars, converting timestamps, and eliminating unused fields
        (so that an objects.create() call would not fail).

        :param data: the object, as sent by Stripe. Parsed from JSON, into a dict
        :type data: dict
        :return: All the members from the input, translated, mutated, etc
        :rtype: dict
        """
        raise NotImplementedError()

    @classmethod
    def create_from_stripe_object(cls, data):
        """
        Create a model instance (not saved to db), using the given data object from Stripe
        :type data: dict
        """
        return cls(**cls.stripe_object_to_record(data))

    def __str__(self):
        return "<{list}>".format(list=", ".join(self.str_parts()))


class StripeEvent(StripeObject):
    class Meta:
        abstract = True

    stripe_api_name = "Event"

    livemode = models.BooleanField(default=False)

    # This is "type" in Stripe
    kind = models.CharField(max_length=250)
    # This is "data" in Stripe
    webhook_message = JSONField()

    @classmethod
    def stripe_object_to_record(cls, data):
        return {
            'stripe_id': data["id"],
            'kind': data["type"],
            'livemode': data["livemode"],
            'webhook_message': data,
        }

    def str_parts(self):
        return [self.kind] + super(StripeEvent, self).str_parts()


class StripeTransfer(StripeObject):
    class Meta:
        abstract = True

    stripe_api_name = "Transfer"

    amount = models.DecimalField(decimal_places=2, max_digits=7)  # Stripe = cents, djstripe = dollars
    status = models.CharField(max_length=25)
    date = models.DateTimeField()
    description = models.TextField(null=True, blank=True)

    # The following fields are nested in the "summary" object
    adjustment_count = models.IntegerField()
    adjustment_fees = models.DecimalField(decimal_places=2, max_digits=7)  # Stripe = cents, djstripe = dollars
    adjustment_gross = models.DecimalField(decimal_places=2, max_digits=7)  # Stripe = cents, djstripe = dollars
    charge_count = models.IntegerField()
    charge_fees = models.DecimalField(decimal_places=2, max_digits=7)  # Stripe = cents, djstripe = dollars
    charge_gross = models.DecimalField(decimal_places=2, max_digits=7)  # Stripe = cents, djstripe = dollars
    collected_fee_count = models.IntegerField()
    collected_fee_gross = models.DecimalField(decimal_places=2, max_digits=7)  # Stripe = cents, djstripe = dollars
    net = models.DecimalField(decimal_places=2, max_digits=7)  # Stripe = cents, djstripe = dollars
    refund_count = models.IntegerField()
    refund_fees = models.DecimalField(decimal_places=2, max_digits=7)  # Stripe = cents, djstripe = dollars
    refund_gross = models.DecimalField(decimal_places=2, max_digits=7)  # Stripe = cents, djstripe = dollars
    validation_count = models.IntegerField()
    validation_fees = models.DecimalField(decimal_places=2, max_digits=7)  # Stripe = cents, djstripe = dollars

    objects = TransferManager()

    def str_parts(self):
        return [
            "amount={amount}".format(amount=self.amount),
            "status={status}".format(status=self.status),
        ] + super(StripeTransfer, self).str_parts()

    def update_status(self):
        self.status = self.api_retrieve().status
        self.save()

    @classmethod
    def stripe_object_to_record(cls, data):
        result = {
            'stripe_id': data["id"],
            "amount": data["amount"] / decimal.Decimal("100"),
            "status": data["status"],
            "date": convert_tstamp(data, "date"),
            "description": data.get("description", ""),
            "adjustment_count": data["summary"]["adjustment_count"],
            "adjustment_fees": data["summary"]["adjustment_fees"],
            "adjustment_gross": data["summary"]["adjustment_gross"],
            "charge_count": data["summary"]["charge_count"],
            "charge_fees": data["summary"]["charge_fees"],
            "charge_gross": data["summary"]["charge_gross"],
            "collected_fee_count": data["summary"]["collected_fee_count"],
            "collected_fee_gross": data["summary"]["collected_fee_gross"],
            "net": data["summary"]["net"] / decimal.Decimal("100"),
            "refund_count": data["summary"]["refund_count"],
            "refund_fees": data["summary"]["refund_fees"],
            "refund_gross": data["summary"]["refund_gross"],
            "validation_count": data["summary"]["validation_count"],
            "validation_fees": data["summary"]["validation_fees"],
        }
        for field in result:
            if field.endswith("fees") or field.endswith("gross"):
                result[field] = result[field] / decimal.Decimal("100")

        return result


class StripeCustomer(StripeObject):
    class Meta:
        abstract = True

    stripe_api_name = "Customer"

    card_fingerprint = models.CharField(max_length=200, blank=True)
    card_last_4 = models.CharField(max_length=4, blank=True)
    card_kind = models.CharField(max_length=50, blank=True)
    card_exp_month = models.PositiveIntegerField(blank=True, null=True)
    card_exp_year = models.PositiveIntegerField(blank=True, null=True)

    @property
    def stripe_customer(self):
        return self.api_retrieve()

    def purge(self):
        """
        Delete all identifying information we have in this record
        """
        self.card_fingerprint = ""
        self.card_last_4 = ""
        self.card_kind = ""
        self.card_exp_month = None
        self.card_exp_year = None

    def has_valid_card(self):
        return all([self.card_fingerprint, self.card_last_4, self.card_kind])

    def sync_card(self):
        stripe_customer = self.stripe_customer

        self.card_fingerprint = stripe_customer.active_card.fingerprint
        self.card_last_4 = stripe_customer.active_card.last4
        self.card_kind = stripe_customer.active_card.type
        self.card_exp_month = stripe_customer.active_card.exp_month
        self.card_exp_year = stripe_customer.active_card.exp_year

    # TODO refactor, deprecation on cu parameter -> stripe_customer
    def sync(self, cu=None):
        stripe_customer = cu or self.stripe_customer
        if getattr(stripe_customer, 'deleted', False):
            # Customer was deleted from stripe
            self.purge()
        elif getattr(stripe_customer, 'active_card', None):
            self.card_fingerprint = stripe_customer.active_card.fingerprint
            self.card_last_4 = stripe_customer.active_card.last4
            self.card_kind = stripe_customer.active_card.type
            self.card_exp_month = stripe_customer.active_card.exp_month
            self.card_exp_year = stripe_customer.active_card.exp_year

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
        resp = StripeCharge.api_create(
            amount=int(amount * 100),  # Convert dollars into cents
            currency=currency,
            customer=self.stripe_id,
            description=description,
            **kwargs
        )
        return resp["id"]

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


class StripeInvoice(StripeObject):
    class Meta:
        abstract = True

    stripe_api_name = "Invoice"

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

    def str_parts(self):
        return [
            "total={total}".format(total=self.total),
            "paid={paid}".format(paid=smart_text(self.paid)),
        ] + super(StripeInvoice, self).str_parts()

    def retry(self):
        if not self.paid and not self.closed:
            inv = self.api_retrieve()
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
    def stripe_object_to_record(cls, data):
        period_end = convert_tstamp(data, "period_end")
        period_start = convert_tstamp(data, "period_start")
        date = convert_tstamp(data, "date")

        return {
            "stripe_id": data["id"],
            "attempted": data["attempted"],
            "closed": data["closed"],
            "paid": data["paid"],
            "period_end": period_end,
            "period_start": period_start,
            "subtotal": data["subtotal"] / decimal.Decimal("100"),
            "total": data["total"] / decimal.Decimal("100"),
            "date": date,
            "charge": data.get("charge") or "",
        }

    def sync(self, data=None):
        for attr, value in data.items():
            setattr(self, attr, value)


class StripeCharge(StripeObject):
    class Meta:
        abstract = True

    stripe_api_name = "Charge"

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

    def str_parts(self):
        return [
            "amount={amount}".format(amount=self.amount),
            "paid={paid}".format(paid=smart_text(self.paid)),
        ] + super(StripeCharge, self).str_parts()

    def calculate_refund_amount(self, amount=None):
        """
        :rtype: int
        :return: amount that can be refunded, in CENTS
        """
        eligible_to_refund = self.amount - (self.amount_refunded or 0)
        if amount:
            amount_to_refund = min(eligible_to_refund, amount)
        else:
            amount_to_refund = eligible_to_refund
        return int(amount_to_refund * 100)

    def refund(self, amount=None, **kwargs):
        """
        Initiate a refund. If amount is not provided, then this will be a full refund
        :return: Stripe charge object
        :rtype: dict
        """
        charge_obj = self.api_retrieve().refund(
            amount=self.calculate_refund_amount(amount=amount),
            **kwargs
        )
        return charge_obj

    def capture(self):
        """
        Capture the payment of an existing, uncaptured, charge. This is the second half of the two-step payment flow,
        where first you created a charge with the capture option set to false.
        See https://stripe.com/docs/api#capture_charge
        """
        return self.api_retrieve().capture()

    @classmethod
    def object_to_customer(cls, manager, data):
        """
        Search the given manager for the customer matching this StripeCharge object

        :param manager: stripe_objects manager for a table of StripeCustomers
        :type manager: StripeObjectManager
        :param data: stripe object
        :type data: dict
        """
        return manager.get_by_json(data, "customer") if "customer" in data else None

    @classmethod
    def object_to_invoice(cls, manager, data):
        """
        Search the given manager for the invoice matching this StripeCharge object
        :param manager: stripe_objects manager for a table of StripeInvoice
        :type manager: StripeObjectManager
        :param data: stripe object
        :type data: dict
        """
        return manager.get_by_json(data, "invoice") if "invoice" in data else None

    @classmethod
    def stripe_object_to_record(cls, data):
        result = {
            "stripe_id": data["id"],
            "card_last_4": data["card"]["last4"],
            "card_kind": data["card"]["type"],
            "amount": (data["amount"] / decimal.Decimal("100")),
            "paid": data["paid"],
            "refunded": data["refunded"],
            "captured": data["captured"],
            "fee": (data["fee"] / decimal.Decimal("100")),
            "disputed": data["dispute"] is not None,
            "charge_created": convert_tstamp(data, "created"),
        }
        if data.get("description"):
            result["description"] = data["description"]
        if data.get("amount_refunded"):
            result["amount_refunded"] = (data["amount_refunded"] / decimal.Decimal("100"))
        if data["refunded"]:
            result["amount_refunded"] = (data["amount"] / decimal.Decimal("100"))

        return result

    def sync(self, data=None):
        for attr, value in data.items():
            setattr(self, attr, value)


INTERVALS = (
    ('week', 'Week',),
    ('month', 'Month',),
    ('year', 'Year',))


class StripePlan(StripeObject):
    class Meta:
        abstract = True

    """A Stripe Plan."""
    stripe_api_name = "Plan"

    @property
    def stripe_plan(self):
        """Return the plan data from Stripe."""
        return self.api_retrieve()
