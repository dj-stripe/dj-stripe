# -*- coding: utf-8 -*-
"""
.. module:: djstripe.stripe_objects
   :synopsis: dj-stripe - Abstract model definitions to provide our view of Stripe's objects

.. moduleauthor:: Bill Huneke (@wahuneke)

This module is an effort to isolate (as much as possible) the API dependent code in one
place. Primarily this is:

1) create models containing the fields that we care about, mapping to Stripe's fields
2) create routines for consistently syncing our database with Stripe's version of the objects
3) centralized routines for creating new database records to match incoming Stripe objects

This module defines abstract models which are then extended in models.py to provide the remaining
dj-stripe functionality.
"""
from contextlib import contextmanager
import datetime
import decimal

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible, smart_text
from jsonfield import JSONField

from model_utils.models import TimeStampedModel
import stripe
from djstripe.managers import StripeObjectManager


stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = getattr(settings, "STRIPE_API_VERSION", "2012-11-07")


def dict_nested_accessor(d, name):
    """
    Access a dictionary value, possibly in a nested dictionary.
    >>> dict_nested_accessor({'id': 'joe'}, 'id')
    >>> "joe"

    >>> dict_nested_accessor({'inner': {'id': 'joe'}}, 'inner.id')
    >>> "joe"

    :type d: dict
    """
    names = name.split(".", 1)
    if len(names) > 1:
        return dict_nested_accessor(d[names[0]], names[1])
    else:
        return d[name]


# Custom fields for all Stripe data. This allows keeping track of which database fields are suitable for sending
# to or receiving from Stripe. Also, allows a few handy extra parameters
class StripeFieldMixin(object):
    # Used if the name at stripe is different from the name in our database
    # Include a . in name if value is nested in dict in Stripe's object
    # (e.g.  stripe_name = "data.id"  -->  obj["data"]["id"])
    stripe_name = None

    # If stripe_name is None, this can also be used to specify a nested value, but
    # the final value is assumed to be the database field name
    # (e.g.    nested_name = "data"    -->  obj["data"][db_field_name]
    nested_name = None

    # This indicates that this field will always appear in a stripe object. It will be
    # an Exception if we try to parse a stripe object that does not include this field
    # in the data. If set to False then null=True attribute will be automatically set
    stripe_required = True

    # If a field was populated in previous API versions but we don't want to drop the old
    # data for some reason, mark it as depricated. This will make sure we never try to send
    # it to Stripe or expect in Stripe data received
    # This setting automatically implies Null=True
    deprecated = False

    def __init__(self, *args, **kwargs):
        self.stripe_name = kwargs.pop('stripe_name', self.stripe_name)
        self.nested_name = kwargs.pop('nested_name', self.nested_name)
        self.stripe_required = kwargs.pop('stripe_required', self.stripe_required)
        self.deprecated = kwargs.pop('deprecated', self.deprecated)
        if not self.stripe_required:
            kwargs["null"] = True

        if self.deprecated:
            kwargs["null"] = True
            kwargs["default"] = None
        super(StripeFieldMixin, self).__init__(*args, **kwargs)

    def stripe_to_db(self, data):
        if not self.deprecated:
            try:
                if self.stripe_name:
                    result = dict_nested_accessor(data, self.stripe_name)
                elif self.nested_name:
                    result = dict_nested_accessor(data, self.nested_name + "." + self.name)
                else:
                    result = data[self.name]
            except KeyError:
                if self.stripe_required:
                    raise
                else:
                    result = None

            return result


class StripeCurrencyField(StripeFieldMixin, models.DecimalField):
    """
    Stripe is always in cents. djstripe stores everything in dollars.
    """
    def __init__(self, *args, **kwargs):
        defaults = {
            'decimal_places': 2,
            'max_digits': 7,
        }
        defaults.update(kwargs)
        super(StripeCurrencyField, self).__init__(*args, **defaults)

    def stripe_to_db(self, data):
        val = super(StripeCurrencyField, self).stripe_to_db(data)
        if val is not None:
            return val / decimal.Decimal("100")


class StripeBooleanField(StripeFieldMixin, models.BooleanField):
    def __init__(self, *args, **kwargs):
        if kwargs.get("deprecated", False):
            raise ImproperlyConfigured("Boolean field cannot be deprecated. Change field type "
                                       "StripeNullBooleanField")
        super(StripeBooleanField, self).__init__(*args, **kwargs)


class StripeNullBooleanField(StripeFieldMixin, models.NullBooleanField):
    pass


class StripeCharField(StripeFieldMixin, models.CharField):
    pass


class StripeIdField(StripeCharField):
    """
    A field with enough space to hold any stripe ID
    """
    def __init__(self, *args, **kwargs):
        defaults = {
            'max_length': 50,
            'blank': False,
            'null': False,
        }
        defaults.update(kwargs)
        super(StripeIdField, self).__init__(*args, **defaults)


class StripeTextField(StripeFieldMixin, models.TextField):
    pass


class StripeDateTimeField(StripeFieldMixin, models.DateTimeField):
    def stripe_to_db(self, data):
        if not self.deprecated:
            return convert_tstamp(super(StripeDateTimeField, self).stripe_to_db(data))


class StripeIntegerField(StripeFieldMixin, models.IntegerField):
    pass


class StripePositiveIntegerField(StripeFieldMixin, models.PositiveIntegerField):
    pass


class StripeJSONField(StripeFieldMixin, JSONField):
    def stripe_to_db(self, data):
        if self.stripe_name:
            # If this is defined, then we grab the value at that location
            return super(StripeJSONField, self).stripe_to_db(data)
        else:
            # Otherwise, we use the whole data block
            return data


@contextmanager
def stripe_temporary_api_key(temp_key):
    """
    A contextmanager

    Temporarily replace the global api_key used in stripe API calls with the given value
    the original value is restored as soon as context exits
    """
    import stripe
    bkp_key = stripe.api_key
    stripe.api_key = temp_key
    yield
    stripe.api_key = bkp_key


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

    stripe_id = StripeIdField(unique=True, stripe_name='id')
    livemode = StripeNullBooleanField(default=False, null=True,
                                      help_text="Null here indicates that data was unavailable. Otherwise, this field "
                                                "indicates whether this record comes from Stripe test mode or live "
                                                "mode operation.")

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
        extend this to add information to the string representation of the object
        :rtype: list of str
        """
        return ["stripe_id={id}".format(id=self.stripe_id)]

    @classmethod
    def stripe_obj_to_record(cls, data):
        """
        Read the appropriate fields from the given Stripe object. Perform appropriate conversions (name conversion,
        currency conversion, timestamp conversion, etc)

        :returns: Create a new dict with this model's field names as keys and appropriate new data as values
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
        return cls(**cls.stripe_obj_to_record(data))

    def __str__(self):
        return "<{list}>".format(list=", ".join(self.str_parts()))


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
    is that the receipt of a webhook event should be 1st) validated by doing an event get using the API version
    of the received hook event. Followed by 2nd) retrieve the referenced object (e.g. the Charge, the Customer, etc)
    using the plugin's supported API version. Then 3rd) process that event using the retrieved object which will, only
    now be in a format that you are certain to understand
    """

    #
    # Stripe API_VERSION: model fields and methods audited to 2015-07-28 - @wahuneke
    #
    stripe_api_name = "Event"

    class Meta:
        abstract = True

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

    def api_retrieve(self):
        # OVERRIDING the parent version of this function
        # Event retrieve is special. For Event we don't retrieve using djstripe's API version. We always retrieve
        # using the API version that was used to send the Event (which depends on the Stripe account holders settings
        with stripe_temporary_api_key(self.received_api_version):
            evt = super(StripeEvent, self).api_retrieve()

        return evt

    def str_parts(self):
        return [self.kind] + super(StripeEvent, self).str_parts()


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

    def sync(self, data=None):
        for attr, value in data.items():
            setattr(self, attr, value)

    @classmethod
    def stripe_obj_to_record(cls, data):
        # Perhaps meaningless legacy code. Nonetheless, preserve it. If charge is null
        # then convert it to ""
        if 'charge' in data and data['charge'] is None:
            data['charge'] = ""
        return super(StripeInvoice, cls).stripe_obj_to_record(data)


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
    def obj_to_customer(cls, manager, data):
        """
        Search the given manager for the customer matching this StripeCharge object
        :param manager: stripe_objects manager for a table of StripeCustomers
        :type manager: StripeObjectManager
        :param data: stripe object
        :type data: dict
        """
        return manager.get_by_json(data, "customer") if "customer" in data else None

    @classmethod
    def obj_to_invoice(cls, manager, data):
        """
        Search the given manager for the invoice matching this StripeCharge object
        :param manager: stripe_objects manager for a table of StripeInvoice
        :type manager: StripeObjectManager
        :param data: stripe object
        :type data: dict
        """
        return manager.get_by_json(data, "invoice") if "invoice" in data else None

    @classmethod
    def stripe_obj_to_record(cls, data):
        data["disputed"] = data["dispute"] is not None
        if data["refunded"]:
            data["amount_refunded"] = data["amount"]

        return super(StripeCharge, cls).stripe_obj_to_record(data)

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


class StripeAccount(StripeObject):
    """
    For now, this is an abstract class, it is here just to provide an interface to the stripe API
    for a few stripe.Account operations we need
    """
    class Meta:
        abstract = True

    @staticmethod
    def get_supported_currencies(api_key):
        """
        Stripe accounts have a list of currencies they support. Get that list for the Stripe account
        corresponding to the api key provided
        :return: list of currency codes
        :rtype: list of str
        """
        # TODO: someday, this will prob be an instance method and we will just have an Account
        # record for "our account"
        with stripe_temporary_api_key(api_key):
            return stripe.Account.retrieve()["currencies_supported"]
