# -*- coding: utf-8 -*-
"""
.. module:: djstripe.stripe_objects
   :synopsis: dj-stripe - Abstract model definitions to provide our view of Stripe's objects

.. moduleauthor:: Bill Huneke (@wahuneke)

This module is an effort to isolate (as much as possible) the API dependent code in one
place. Primarily this is:

1) create models containing the fields that we care about, mapping to Stripe's fields
2) create methods for consistently syncing our database with Stripe's version of the objects
3) centralized methods for creating new database records to match incoming Stripe objects

This module defines abstract models which are then extended in models.py to provide the remaining
dj-stripe functionality.
"""


import decimal

from django.conf import settings
from django.db import models
from django.utils.encoding import python_2_unicode_compatible, smart_text

from model_utils.models import TimeStampedModel

from .context_managers import stripe_temporary_api_version
from .fields import (StripeFieldMixin, StripeCharField, StripeDateTimeField, StripeCurrencyField,
                     StripeIntegerField, StripeTextField, StripePositiveIntegerField, StripeIdField,
                     StripeBooleanField, StripeNullBooleanField, StripeJSONField)
from .managers import StripeObjectManager


import stripe
stripe.api_version = getattr(settings, "STRIPE_API_VERSION", "2013-02-11")


# ============================================================================ #
#                           Stripe Object Base                                 #
# ============================================================================ #


@python_2_unicode_compatible
class StripeObject(TimeStampedModel):
    # This must be defined in descendants of this model/mixin
    # e.g. "Event", "Charge", "Customer", etc.
    stripe_api_name = None
    objects = models.Manager()
    stripe_objects = StripeObjectManager()

    stripe_id = StripeIdField(unique=True, stripe_name='id')
    livemode = StripeNullBooleanField(default=False, null=True, stripe_required=False,
                                      help_text="Null here indicates that the livemode status is unknown "
                                                "or was previously unrecorded. Otherwise, this field indicates "
                                                "whether this record comes from Stripe test mode or live "
                                                "mode operation.")
    metadata = StripeJSONField(blank=True, stripe_required=False, help_text="A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.")

    class Meta:
        abstract = True

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

    def api_retrieve(self, expand=None):
        """
        Implement very commonly used API function 'retrieve'
        """
        # Run stripe.X.retreive(id)
        return type(self).api().retrieve(id=self.stripe_id, api_key=settings.STRIPE_SECRET_KEY, expand=expand)

    @classmethod
    def api_create(cls, **kwargs):
        """
        Call the stripe API's create operation for this model
        """
        return cls.api().create(api_key=settings.STRIPE_SECRET_KEY, **kwargs)

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
        result = dict()
        # Iterate over all the fields that we know are related to Stripe, let each field work its own magic
        for field in filter(lambda x: isinstance(x, StripeFieldMixin), cls._meta.fields):
            result[field.name] = field.stripe_to_db(data)

        return result

    @classmethod
    def create_from_stripe_object(cls, data):
        """
        Create a model instance (not saved to db), using the given data object from Stripe
        :type data: dict
        """
        return cls(**cls.stripe_object_to_record(data))

    @classmethod
    def get_or_create_from_stripe_object(cls, data, field_name="id"):
        try:
            return cls.stripe_objects.get_by_json(data, field_name), False
        except cls.DoesNotExist:
            return cls.create_from_stripe_object(data), True

    def __str__(self):
        return "<{list}>".format(list=", ".join(self.str_parts()))


class StripeSource(StripeObject):

    class Meta:
        abstract = True


# ============================================================================ #
#                               Stripe Objects                                 #
# ============================================================================ #

class StripeCharge(StripeObject):

    class Meta:
        abstract = True

    stripe_api_name = "Charge"

    card_last_4 = StripeCharField(max_length=4, blank=True, stripe_name="card.last4")
    card_kind = StripeCharField(max_length=50, blank=True, stripe_name="card.type")
    amount = StripeCurrencyField(null=True)
    amount_refunded = StripeCurrencyField(null=True, stripe_required=False)
    description = StripeTextField(blank=True, stripe_required=False)
    paid = StripeNullBooleanField(null=True)
    disputed = StripeNullBooleanField(null=True)
    refunded = StripeNullBooleanField(null=True)
    captured = StripeNullBooleanField(null=True)
    fee = StripeCurrencyField(null=True)

    # DEPRECATED fields
    receipt_sent = StripeNullBooleanField(deprecated=True)
    charge_created = StripeDateTimeField(deprecated=True, stripe_name="created")

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

    def refund(self, amount=None):
        """
        Initiate a refund. If amount is not provided, then this will be a full refund
        :return: Stripe charge object
        :rtype: dict
        """
        charge_obj = self.api_retrieve().refund(
            amount=self.calculate_refund_amount(amount=amount)
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
    def object_to_customer(cls, target_cls, data):
        """
        Search the given manager for the Customer matching this StripeCharge object's ``customer`` field.

        :param target_cls: The target class
        :type target_cls: StripeCustomer
        :param data: stripe object
        :type data: dict
        """

        if "customer" in data and data["customer"]:
            return target_cls.get_or_create_from_stripe_object(data, "customer")[0]

    @classmethod
    def object_to_invoice(cls, target_cls, data):
        """
        Search the given manager for the Invoice matching this StripeCharge object's ``invoice`` field.

        :param target_cls: The target class
        :type target_cls: StripeInvoice
        :param data: stripe object
        :type data: dict
        """

        if "invoice" in data and data["invoice"]:
            return target_cls.get_or_create_from_stripe_object(data, "invoice")[0]

    @classmethod
    def object_to_source(cls, target_cls, data):
        """
        Search the given manager for the source matching this StripeCharge object's ``source`` field.
        Note that the source field is already expanded in each request.

        :param target_cls: The target class
        :type target_cls: StripeSource
        :param data: stripe object
        :type data: dict
        """

        if "source" in data and data["source"]:
            return target_cls.get_or_create_from_stripe_object(data["source"])[0]

    @classmethod
    def object_destination_to_account(cls, target_cls, data):
        """
        Search the given manager for the Account matching this StripeCharge object's ``destination`` field.

        :param target_cls: The target class
        :type target_cls: StripeAccount
        :param data: stripe object
        :type data: dict
        """

        if "destination" in data and data["destination"]:
            return target_cls.get_or_create_from_stripe_object(data, "destination")[0]

    @classmethod
    def stripe_object_to_record(cls, data):
        data["disputed"] = data["dispute"] is not None

        return super(StripeCharge, cls).stripe_object_to_record(data)

    def sync(self, data=None):
        for attr, value in data.items():
            setattr(self, attr, value)


class StripeCustomer(StripeObject):

    class Meta:
        abstract = True

    stripe_api_name = "Customer"

    card_fingerprint = StripeCharField(max_length=200, blank=True)
    card_last_4 = StripeCharField(max_length=4, blank=True)
    card_kind = StripeCharField(max_length=50, blank=True)
    card_exp_month = StripePositiveIntegerField(blank=True, null=True)
    card_exp_year = StripePositiveIntegerField(blank=True, null=True)

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

        # TODO: Refactor when InvoiceItem becomes a StripeObject
        stripe.InvoiceItem.create(api_key=settings.STRIPE_SECRET_KEY,
            amount=int(amount * 100),  # Convert dollars into cents
            currency=currency,
            customer=self.stripe_id,
            description=description,
            invoice=invoice_id,
        )

    def sync_card(self):
        self.card_fingerprint = self.stripe_customer.active_card.fingerprint
        self.card_last_4 = self.stripe_customer.active_card.last4
        self.card_kind = self.stripe_customer.active_card.type
        self.card_exp_month = self.stripe_customer.active_card.exp_month
        self.card_exp_year = self.stripe_customer.active_card.exp_year

    def sync(self):
        if getattr(self.stripe_customer, 'deleted', False):
            # Customer was deleted from stripe
            self.purge()
        elif getattr(self.stripe_customer, 'active_card', None):
            self.card_fingerprint = self.stripe_customer.active_card.fingerprint
            self.card_last_4 = self.stripe_customer.active_card.last4
            self.card_kind = self.stripe_customer.active_card.type
            self.card_exp_month = self.stripe_customer.active_card.exp_month
            self.card_exp_year = self.stripe_customer.active_card.exp_year


class StripeCard(StripeSource):

    class Meta:
        abstract = True

    stripe_api_name = "Card"


class StripeSubscription(StripeObject):

    class Meta:
        abstract = True

    stripe_api_name = "Subscription"


class StripePlan(StripeObject):

    class Meta:
        abstract = True

    stripe_api_name = "Plan"

    @property
    def stripe_plan(self):
        """Return the plan data from Stripe."""
        return self.api_retrieve()


class StripeInvoice(StripeObject):

    class Meta:
        abstract = True

    stripe_api_name = "Invoice"

    attempted = StripeNullBooleanField()
    attempts = StripePositiveIntegerField(null=True, stripe_name="attempt_count")
    closed = StripeBooleanField(default=False)
    paid = StripeBooleanField(default=False)
    period_end = StripeDateTimeField()
    period_start = StripeDateTimeField()
    subtotal = StripeCurrencyField()
    total = StripeCurrencyField()
    date = StripeDateTimeField()
    charge = StripeIdField(max_length=50, blank=True, stripe_required=False, default="")

    def str_parts(self):
        return [
            "total={total}".format(total=self.total),
            "paid={paid}".format(paid=smart_text(self.paid)),
        ] + super(StripeInvoice, self).str_parts()

    def retry(self):
        if not self.paid and not self.closed:
            stripe_invoice = self.api_retrieve()
            updated_stripe_invoice = stripe_invoice.pay()  # pay() throws an exception if the charge is not successful.
            self.sync_from_stripe_data(updated_stripe_invoice)
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
        # Perhaps meaningless legacy code. Nonetheless, preserve it. If charge is null
        # then convert it to ""
        if 'charge' in data and data['charge'] is None:
            data['charge'] = ""
        return super(StripeInvoice, cls).stripe_object_to_record(data)

    def sync(self, data=None):
        for attr, value in data.items():
            setattr(self, attr, value)


class StripeInvoiceItem(StripeObject):

    class Meta:
        abstract = True

    stripe_api_name = "InvoiceItem"


class StripeTransfer(StripeObject):

    class Meta:
        abstract = True

    stripe_api_name = "Transfer"

    amount = StripeCurrencyField()
    status = StripeCharField(max_length=25)
    date = StripeDateTimeField(help_text="Date the transfer is scheduled to arrive at destination")
    description = StripeTextField(null=True, blank=True, stripe_required=False)

    # The following fields are nested in the "summary" object
    adjustment_count = StripeIntegerField(nested_name="summary")
    adjustment_fees = StripeCurrencyField(nested_name="summary")
    adjustment_gross = StripeCurrencyField(nested_name="summary")
    charge_count = StripeIntegerField(nested_name="summary")
    charge_fees = StripeCurrencyField(nested_name="summary")
    charge_gross = StripeCurrencyField(nested_name="summary")
    collected_fee_count = StripeIntegerField(nested_name="summary")
    collected_fee_gross = StripeCurrencyField(nested_name="summary")
    net = StripeCurrencyField(nested_name="summary")
    refund_count = StripeIntegerField(nested_name="summary")
    refund_fees = StripeCurrencyField(nested_name="summary")
    refund_gross = StripeCurrencyField(nested_name="summary")
    validation_count = StripeIntegerField(nested_name="summary")
    validation_fees = StripeCurrencyField(nested_name="summary")

    def str_parts(self):
        return [
            "amount={amount}".format(amount=self.amount),
            "status={status}".format(status=self.status),
        ] + super(StripeTransfer, self).str_parts()

    def update_status(self):
        self.status = self.api_retrieve().status
        self.save()


class StripeAccount(StripeObject):

    class Meta:
        abstract = True

    stripe_api_name = "Account"


class StripeEvent(StripeObject):
    """
    Events are POSTed to our webhook url. They provide information about a Stripe event that just happened. Events
    are processed in detail by their respective models (charge events by the Charge model, etc).

    Events are initially _UNTRUSTED_, as it is possible for any web entity to post any data to our webhook url. Data
    posted may be valid Stripe information, garbage, or even malicious. The 'valid' flag in this model monitors this.

    API VERSIONING
    ====
    This is a tricky matter when it comes to webhooks. See the discussion here:
        https://groups.google.com/a/lists.stripe.com/forum/#!topic/api-discuss/h5Y6gzNBZp8

    In this discussion, it is noted that Webhooks are produced in one API version, which will usually be
    different from the version supported by Stripe plugins (such as djstripe). The solution, described there,
    is:

        1) validate the receipt of a webhook event by doing an event get using the API version of the received hook event.
        2) retrieve the referenced object (e.g. the Charge, the Customer, etc) using the plugin's supported API version.
        3) process that event using the retrieved object which will, only now, be in a format that you are certain to understand
    """

    #
    # Stripe API_VERSION: model fields and methods audited to 2015-07-28 - @wahuneke
    #
    class Meta:
        abstract = True

    stripe_api_name = "Event"

    kind = StripeCharField(stripe_name="type", max_length=250, help_text="Stripe's event description code")
    request_id = StripeCharField(max_length=50, null=True, blank=True, stripe_name="request",
                                 help_text="Information about the request that triggered this event, for traceability "
                                           "purposes. If empty string then this is an old entry without that data. If "
                                           "Null then this is not an old entry, but a Stripe 'automated' event with "
                                           "no associated request.")
    event_timestamp = StripeDateTimeField(null=True, stripe_name="created",
                                          help_text="Empty for old entries. For all others, this entry field gives "
                                                    "the timestamp of the time when the event occured from Stripe's "
                                                    "perspective. This is as opposed to the time when we received "
                                                    "notice of the event, which is not guaranteed to be the same time"
                                                    "and which is recorded in a different field.")
    received_api_version = StripeCharField(max_length=15, blank=True, stripe_name="api_version",
                                           help_text="the API version at which the event data was rendered. Blank for "
                                                     "old entries only, all new entries will have this value")
    webhook_message = StripeJSONField(help_text="data received at webhook. data should be considered to be garbage "
                                                "until validity check is run and valid flag is set", stripe_name="data")

    def str_parts(self):
        return [self.kind] + super(StripeEvent, self).str_parts()

    def api_retrieve(self):
        # OVERRIDING the parent version of this function
        # Event retrieve is special. For Event we don't retrieve using djstripe's API version. We always retrieve
        # using the API version that was used to send the Event (which depends on the Stripe account holders settings
        with stripe_temporary_api_version(self.received_api_version):
            stripe_event = super(StripeEvent, self).api_retrieve()

        return stripe_event
