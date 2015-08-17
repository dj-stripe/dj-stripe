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
from polymorphic import PolymorphicModel

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
    expand_fields = None

    objects = models.Manager()
    stripe_objects = StripeObjectManager()

    stripe_id = StripeIdField(unique=True, stripe_name='id')
    livemode = StripeNullBooleanField(default=False, null=True, stripe_required=False,
                                      help_text="Null here indicates that the livemode status is unknown "
                                                "or was previously unrecorded. Otherwise, this field indicates "
                                                "whether this record comes from Stripe test mode or live "
                                                "mode operation.")
    stripe_timestamp = StripeDateTimeField(null=True, stripe_required=False, stripe_name="created", help_text="The datetime this object was created in stripe.")
    metadata = StripeJSONField(blank=True, stripe_required=False, help_text="A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.")
    description = StripeTextField(blank=True, stripe_required=False, help_text="A description of this object.")

    class Meta:
        abstract = True

    @classmethod
    def _api(cls):
        """
        Get the api object for this type of stripe object (requires
        stripe_api_name attribute to be set on model).
        """
        if cls.stripe_api_name is None:
            raise NotImplementedError("StripeObject descendants are required to define "
                                      "the stripe_api_name attribute")
        # e.g. stripe.Event, stripe.Charge, etc
        return getattr(stripe, cls.stripe_api_name)

    def api_retrieve(self, api_key=settings.STRIPE_SECRET_KEY):
        """
        Implement very commonly used API function 'retrieve'.

        :param api_key: The api key to use for this request. Defualts to settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """

        # Run stripe.X.retreive(id)
        return type(self)._api().retrieve(id=self.stripe_id, api_key=api_key, expand=self.expand_fields)

    @classmethod
    def _api_create(cls, api_key=settings.STRIPE_SECRET_KEY, **kwargs):
        """
        Call the stripe API's create operation for this model

        :param api_key: The api key to use for this request. Defualts to settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """

        return cls._api().create(api_key=api_key, **kwargs)

    def _api_delete(self, api_key=settings.STRIPE_SECRET_KEY):
        """
        Call the stripe API's delete operation for this model

        :param api_key: The api key to use for this request. Defualts to settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """

        self.api_retrieve(api_key).delete()

    def str_parts(self):
        """
        Extend this to add information to the string representation of the object

        :rtype: list of str
        """
        return ["stripe_id={id}".format(id=self.stripe_id)]

    @classmethod
    def manipulate_stripe_object_hook(cls, data):
        """
        Gets called by this object's stripe object conversion method just before conversion.
        Use this to populate custom fields in a StripeObject from stripe data.
        """
        return data

    @classmethod
    def _stripe_object_to_record(cls, data):
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

        manipulated_data = cls.manipulate_stripe_object_hook(data)

        result = dict()
        # Iterate over all the fields that we know are related to Stripe, let each field work its own magic
        for field in filter(lambda x: isinstance(x, StripeFieldMixin), cls._meta.fields):
            result[field.name] = field.stripe_to_db(manipulated_data)

        return result

    def attach_objects_hook(self, cls, data):
        """
        Gets called by this object's create and sync methods just before save.
        Use this to populate fields before the model is saved.
        """

        pass

    @classmethod
    def _create_from_stripe_object(cls, data):
        """
        Create a model instance using the given data object from Stripe
        :type data: dict
        """
        instance = cls(**cls._stripe_object_to_record(data))
        instance.attach_objects_hook(cls, data)
        instance.save()

        return instance

    @classmethod
    def get_or_create_from_stripe_object(cls, data, field_name="id"):
        try:
            return cls.stripe_objects.get_by_json(data, field_name), False
        except cls.DoesNotExist:
            # Grab the stripe data for a nested object
            if field_name != "id":
                cls_instance = cls(stripe_id=data[field_name])
                data = cls_instance.api_retrieve()

            return cls._create_from_stripe_object(data), True

    @classmethod
    def stripe_object_to_customer(cls, target_cls, data):
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
    def stripe_object_to_source(cls, target_cls, data):
        """
        Search the given manager for the source matching this StripeCharge object's ``source`` field.
        Note that the source field is already expanded in each request, and that it is required.

        :param target_cls: The target class
        :type target_cls: StripeSource
        :param data: stripe object
        :type data: dict
        """

        return target_cls.get_or_create_from_stripe_object(data["source"])[0]

    def _sync(self, data):
        for attr, value in data.items():
            setattr(self, attr, value)

    @classmethod
    def sync_from_stripe_data(cls, data):
        instance, created = cls.get_or_create_from_stripe_object(data)

        if not created:
            instance._sync(cls._stripe_object_to_record(data))
            instance.attach_objects_hook(cls, data)
            instance.save()

        return instance

    def __str__(self):
        return smart_text("<{list}>".format(list=", ".join(self.str_parts())))


class StripeSource(PolymorphicModel, StripeObject):
    customer = models.ForeignKey("Customer", blank=True, related_name="sources")


# ============================================================================ #
#                               Stripe Objects                                 #
# ============================================================================ #

class StripeCharge(StripeObject):
    """
    To charge a credit or a debit card, you create a charge object. You can
    retrieve and refund individual charges as well as list all charges. Charges
    are identified by a unique random ID. (Source: https://stripe.com/docs/api/python#charges)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:
    * object: Unnecessary. Just check the model name.
    * refunds: #
    * application_fee: #. Coming soon with stripe connect functionality
    * balance_transaction: #
    * dispute: #; Mapped to a ``disputed`` boolean.
    * fraud_details: Mapped to a ``fraudulent`` boolean.
    * receipt_email: Unnecessary. Defaults to customer's email. Create a feature request if this is functionality you need.
    * receipt_number: Unnecessary.

    Stripe API_VERSION: model fields and methods audited to 2015-07-28 - @kavdev
    """

    STATUS_CHOICES = [(status, status.title()) for status in ["succeeded", "failed"]]
    CARD_ERROR_CODES = ["invalid_number", "invalid_expiry_month", "invalid_expiry_year",
                        "invalid_cvc", "incorrect_number", "expired_card",
                        "incorrect_cvc", "incorrect_zip", "card_declined",
                        "missing", "processing_error", "rate_limit"]
    CARD_ERROR_CODE_CHOICES = [(error_code, error_code.replace("_", " ").title()) for error_code in CARD_ERROR_CODES]

    class Meta:
        abstract = True

    stripe_api_name = "Charge"
    expand_fields = ["balance_transaction"]

    amount = StripeCurrencyField(null=True, help_text="Amount charged.")
    amount_refunded = StripeCurrencyField(null=True, help_text="Amount refunded (can be less than the amount attribute on the charge if a partial refund was issued).")
    captured = StripeBooleanField(default=False, help_text="If the charge was created without capturing, this boolean represents whether or not it is still uncaptured or has since been captured.")
    currency = StripeCharField(max_length=3, null=True, help_text="Three-letter ISO currency code representing the currency in which the charge was made.")
    paid = StripeBooleanField(default=False, help_text="``true`` if the charge succeeded, or was successfully authorized for later capture, ``false`` otherwise.")
    refunded = StripeBooleanField(default=False, help_text="Whether or not the charge has been fully refunded. If the charge is only partially refunded, this attribute will still be false.")
    status = StripeCharField(max_length=10, null=True, choices=STATUS_CHOICES, help_text="The status of the payment is either ``succeeded`` or ``failed``.")
    failure_code = StripeCharField(max_length=30, null=True, choices=CARD_ERROR_CODE_CHOICES, help_text="Error code explaining reason for charge failure if available.")
    failure_message = StripeTextField(null=True, help_text="Message to user further explaining reason for charge failure if available.")
    shipping = StripeJSONField(null=True, help_text="Shipping information for the charge")

    fee = StripeCurrencyField(null=True, nested_name="balance_transaction")

    # dj-stripe custom stripe fields. Don't try to send these.
    source_type = StripeCharField(max_length=20, null=True, stripe_name="source.object", help_text="The payment source type. If the payment source is supported by dj-stripe, a corresponding model is attached to this Charge via a foreign key matching this field.")
    source_stripe_id = StripeIdField(null=True, stripe_name="source.id", help_text="The payment source id.")
    disputed = StripeBooleanField(default=False, help_text="Whether or not this charge is disputed.")
    fraudulent = StripeBooleanField(default=False, help_text="Whether or not this charge was marked as fraudulent.")

    # DEPRECATED fields.
    card_last_4 = StripeCharField(max_length=4, deprecated=True)
    card_kind = StripeCharField(max_length=50, deprecated=True)

    def str_parts(self):
        return [
            "amount={amount}".format(amount=self.amount),
            "paid={paid}".format(paid=smart_text(self.paid)),
        ] + super(StripeCharge, self).str_parts()

    def _calculate_refund_amount(self, amount=None):
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

    def refund(self, amount=None, reason=None):
        """
        Initiate a refund. If amount is not provided, then this will be a full refund.

        :param amount: A positive decimal amount representing how much of this charge
            to refund. Can only refund up to the unrefunded amount remaining of the charge.
        :trye amount: Decimal
        :param reason: String indicating the reason for the refund. If set, possible values
            are ``duplicate``, ``fraudulent``, and ``requested_by_customer``. Specifying
            ``fraudulent`` as the reason when you believe the charge to be fraudulent will
            help Stripe improve their fraud detection algorithms.

        :return: Stripe charge object
        :rtype: dict
        """
        charge_obj = self.api_retrieve().refund(
            amount=self._calculate_refund_amount(amount=amount),
            reason=reason
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
    def stripe_object_to_invoice(cls, target_cls, data):
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
    def stripe_object_destination_to_account(cls, target_cls, data):
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
    def stripe_object_to_transfer(cls, target_cls, data):
        """
        Search the given manager for the Transfer matching this StripeCharge object's ``transfer`` field.

        :param target_cls: The target class
        :type target_cls: StripeTransfer
        :param data: stripe object
        :type data: dict
        """

        if "transfer" in data and data["transfer"]:
            return target_cls.get_or_create_from_stripe_object(data, "transfer")[0]

    @classmethod
    def manipulate_stripe_object_hook(cls, data):
        data["disputed"] = data["dispute"] is not None

        # Assessments reported by you have the key user_report and, if set,
        # possible values of safe and fraudulent. Assessments from Stripe have
        # the key stripe_report and, if set, the value fraudulent.
        data["fraudulent"] = data["fraud_details"] and list(data["fraud_details"].values())[0] == "fraudulent"

        return data


class StripeCustomer(StripeObject):
    """
    Customer objects allow you to perform recurring charges and track multiple charges that are
    associated with the same customer. (Source: https://stripe.com/docs/api/python#charges)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:
    * object: Unnecessary. Just check the model name.
    * discount: #
    * email: Unnecessary. See ``Customer.subscriber.email``.

    Stripe API_VERSION: model fields and methods audited to 2015-07-28 - @kavdev
    """

    class Meta:
        abstract = True

    stripe_api_name = "Customer"

    account_balance = StripeIntegerField(null=True, help_text="Current balance, if any, being stored on the customer's account. If negative, the customer has credit to apply to the next invoice. If positive, the customer has an amount owed that will be added to the next invoice. The balance does not refer to any unpaid invoices; it solely takes into account amounts that have yet to be successfully applied to any invoice. This balance is only taken into account for recurring charges.")
    currency = StripeCharField(max_length=3, null=True, help_text="The currency the customer can be charged in for recurring billing purposes (subscriptions, invoices, invoice items).")
    delinquent = StripeBooleanField(default=False, help_text="Whether or not the latest charge for the customer’s latest invoice has failed.")

    # Deprecated fields
    card_fingerprint = StripeCharField(max_length=200, deprecated=True)
    card_last_4 = StripeCharField(max_length=4, deprecated=True)
    card_kind = StripeCharField(max_length=50, deprecated=True)
    card_exp_month = StripePositiveIntegerField(deprecated=True)
    card_exp_year = StripePositiveIntegerField(deprecated=True)

    def purge(self):
        """Delete all identifying information we have in this record."""
        self.card_fingerprint = ""
        self.card_last_4 = ""
        self.card_kind = ""
        self.card_exp_month = None
        self.card_exp_year = None

    def has_valid_card(self):
        """remove in favor of sources"""
        return all([self.card_fingerprint, self.card_last_4, self.card_kind])

    def charge(self, amount, currency="usd", source=None, description=None, capture=True,
               statement_descriptor=None, metadata=None, shipping=None):
        """
        Creates a charge for this customer.

        :param amount: The amount to charge.
        :type amount: Decimal. Precision is 2; anything more will be ignored.
        :param currency: 3-letter ISO code for currency
        :type currency: string
        :param source: The source to use for this charge. Must be a source attributed to this customer. If None,
                       the customer's default source is used.
        :type source: StripeSource
        :param description: An arbitrary string.
        :type description: string
        :param metadata: A set of key/value pairs useful for storing additional information.
        :type metadata: dict
        :param capture: Whether or not to immediately capture the charge. When false, the charge issues an
                        authorization (or pre-authorization), and will need to be captured later. Uncaptured
                        charges expire in 7 days.
        :type capture: bool
        :param statement_descriptor: An arbitrary string to be displayed on the customer's credit card statement.
        :type statement_descriptor: string
        """
        if not isinstance(amount, decimal.Decimal):
            raise ValueError("You must supply a decimal value representing dollars.")

        new_charge = StripeCharge._api_create(
            amount=int(amount * 100),  # Convert dollars into cents
            currency=currency,
            customer=self.stripe_id,
            source=source,
            description=description,
            statement_descriptor=statement_descriptor,
            metatdata=metadata,
            shipping=shipping,
        )

        return new_charge["id"]

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

    def _sync_card(self):
        stripe_customer = self.api_retrieve()

        self.card_fingerprint = stripe_customer.active_card.fingerprint
        self.card_last_4 = stripe_customer.active_card.last4
        self.card_kind = stripe_customer.active_card.type
        self.card_exp_month = stripe_customer.active_card.exp_month
        self.card_exp_year = stripe_customer.active_card.exp_year

    def _sync(self):
        stripe_customer = self.api_retrieve()

        if getattr(stripe_customer, 'deleted', False):
            # Customer was deleted from stripe
            self.purge()
        elif getattr(stripe_customer, 'active_card', None):
            self._sync_card()


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

    @classmethod
    def get_connected_account_from_token(cls, access_token):
        account_data = cls._api().retrieve(api_key=access_token)

        return cls.get_or_create_from_stripe_object(account_data)[0]

    @classmethod
    def get_default_account(cls):
        account_data = cls._api().retrieve(api_key=settings.STRIPE_SECRET_KEY)

        return cls.get_or_create_from_stripe_object(account_data)[0]


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

    Stripe API_VERSION: model fields and methods audited to 2015-07-28 - @wahuneke
    """

    class Meta:
        abstract = True

    stripe_api_name = "Event"

    type = StripeCharField(max_length=250, help_text="Stripe's event description code")
    request_id = StripeCharField(max_length=50, null=True, blank=True, stripe_name="request",
                                 help_text="Information about the request that triggered this event, for traceability "
                                           "purposes. If empty string then this is an old entry without that data. If "
                                           "Null then this is not an old entry, but a Stripe 'automated' event with "
                                           "no associated request.")
    received_api_version = StripeCharField(max_length=15, blank=True, stripe_name="api_version",
                                           help_text="the API version at which the event data was rendered. Blank for "
                                                     "old entries only, all new entries will have this value")
    webhook_message = StripeJSONField(stripe_name="data", help_text="data received at webhook. data should be considered to be garbage "
                                                                    "until validity check is run and valid flag is set")

    def str_parts(self):
        return [self.type] + super(StripeEvent, self).str_parts()

    def api_retrieve(self):
        # OVERRIDING the parent version of this function
        # Event retrieve is special. For Event we don't retrieve using djstripe's API version. We always retrieve
        # using the API version that was used to send the Event (which depends on the Stripe account holders settings
        with stripe_temporary_api_version(self.received_api_version):
            stripe_event = super(StripeEvent, self).api_retrieve()

        return stripe_event
