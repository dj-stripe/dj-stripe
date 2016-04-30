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


from copy import deepcopy
import decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible, smart_text
from model_utils.models import TimeStampedModel
from polymorphic.models import PolymorphicModel
import stripe

from djstripe.fields import StripeDateTimeField, StripeJSONField, \
    StripeBooleanField, StripeTextField

from .context_managers import stripe_temporary_api_version
from .exceptions import StripeObjectManipulationException
from .fields import (StripeFieldMixin, StripeCharField, StripeDateTimeField, StripePercentField, StripeCurrencyField,
                     StripeIntegerField, StripeTextField, StripePositiveIntegerField, StripeIdField,
                     StripeBooleanField, StripeNullBooleanField, StripeJSONField)
from .managers import StripeObjectManager


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
        Search the given manager for the Customer matching this object's ``customer`` field.

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
        Search the given manager for the source matching this object's ``source`` field.
        Note that the source field is already expanded in each request, and that it is required.

        :param target_cls: The target class
        :type target_cls: StripeSource
        :param data: stripe object
        :type data: dict
        """

        return target_cls.get_or_create_from_stripe_object(data["source"])[0]

    def _sync(self, record_data):
        for attr, value in record_data.items():
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
    customer = models.ForeignKey("Customer", related_name="sources")


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

    @classmethod
    def stripe_object_default_source_to_source(cls, target_cls, data):
        """
        Search the given manager for the source matching this StripeCharge object's ``default_source`` field.
        Note that the source field is already expanded in each request, and that it is required.

        :param target_cls: The target class
        :type target_cls: StripeSource
        :param data: stripe object
        :type data: dict
        """

        return target_cls.get_or_create_from_stripe_object(data["default_source"])[0]

    def purge(self):
        """Delete all identifying information we have in this record."""

        # Delete deprecated card details
        self.card_fingerprint = ""
        self.card_last_4 = ""
        self.card_kind = ""
        self.card_exp_month = None
        self.card_exp_year = None

    def add_card(self, source, set_default=True):
        """
        Adds a card to this customer's account.

        :param source: Either a token, like the ones returned by our Stripe.js, or a dictionary containing a user’s credit card details. Stripe will automatically validate the card.
        :type source: string, dict
        :param set_default: Whether or not to set the source as the customer's default source
        :type set_default: boolean

        """

        stripe_customer = self.api_retrieve()
        stripe_card = stripe_customer.sources.create(source=source)

        if set_default:
            stripe_customer.default_source = stripe_card["id"]
            stripe_customer.save()

        return stripe_card

    def charge(self, amount, currency, source=None, description=None, capture=None,
               statement_descriptor=None, metadata=None, destination=None, application_fee=None, shipping=None):
        """
        Creates a charge for this customer.

        :param amount: The amount to charge.
        :type amount: Decimal. Precision is 2; anything more will be ignored.
        :param currency: 3-letter ISO code for currency
        :type currency: string
        :param source: The source to use for this charge. Must be a source attributed to this customer. If None,
                       the customer's default source is used. Can be either the id of the source or the source object itself.
        :type source: string, StripeSource
        :param description: An arbitrary string.
        :type description: string
        :param capture: Whether or not to immediately capture the charge. When false, the charge issues an
                        authorization (or pre-authorization), and will need to be captured later. Uncaptured
                        charges expire in 7 days. Default is True
        :type capture: bool
        :param statement_descriptor: An arbitrary string to be displayed on the customer's credit card statement.
        :type statement_descriptor: string
        :param metadata: A set of key/value pairs useful for storing additional information.
        :type metadata: dict
        :param destination: An account to make the charge on behalf of.
        :type destination: Account
        :param application_fee: A fee that will be applied to the charge and transfered to the platform owner's account.
        :type application_fee: Decimal. Precision is 2; anything more will be ignored.

        """

        if not isinstance(amount, decimal.Decimal):
            raise ValueError("You must supply a decimal value representing dollars.")

        # Convert StripeSource to stripe_id
        if source and isinstance(source, StripeSource):
            source = source.stripe_id

        stripe_charge = StripeCharge._api_create(
            amount=int(amount * 100),  # Convert dollars into cents
            currency=currency,
            customer=self.stripe_id,
            source=source,
            description=description,
            capture=capture,
            statement_descriptor=statement_descriptor,
            metatdata=metadata,
            destination=destination.stripe_id if destination else None,  # Convert Account to stripe_id
            application_fee=int(amount * 100),  # Convert dollars into cents
            shipping=shipping,
        )

        return stripe_charge

    def subscribe(self, plan, coupon=None, trial_end=None, quantity=None, application_fee_percent=None, tax_percent=None, metadata=None):
        """
        Subscribes this customer to a plan.

        Parameters not implemented:
        * source: Subscriptions use the customer's default source. Including the source parameter creates a new source for this customer and overrides the default source. This
                  functionality is not desired; add a source to the customer before attempting to add a subscription.

        :param plan: The plan to which to subscribe the customer.
        :type plan: string (plan ID)
        :param coupon: The code of the coupon to apply to this subscription. A coupon applied to a subscription will only affect invoices created for that particular subscription.
        :type coupon: string
        :param trial_end: The end datetime of the trial period the customer will get before being charged for the first time. If set, this will override the default trial
                           period of the plan the customer is being subscribed to. The special value ``now`` can be provided to end the customer's trial immediately.
        :type trial_end: datetime
        :param quantity: The quantity applied to this subscription. Default is 1.
        :type quantity: integer
        :param application_fee_percent: This represents the percentage of the subscription invoice subtotal that will be transferred to the application owner’s Stripe account.
                                        The request must be made with an OAuth key in order to set an application fee percentage.
        :type application_fee_percent: Decimal. Precision is 2; anything more will be ignored. A positive decimal between 1 and 100.
        :param tax_percent: This represents the percentage of the subscription invoice subtotal that will be calculated and added as tax to the final amount each billing period.
        :type tax_percent: Decimal. Precision is 2; anything more will be ignored. A positive decimal between 1 and 100.
        :param metadata: A set of key/value pairs useful for storing additional information.
        :type metadata: dict
        """

        stripe_subscription = StripeSubscription._api_create(
            plan=plan,
            coupon=coupon,
            trial_end=trial_end,  # Automatically gets onverted to a unix timestamp by stripe
            quantity=quantity,
            application_fee_percent=application_fee_percent,
            tax_percent=tax_percent,
            metadata=metadata
        )

        return stripe_subscription

    def add_invoice_item(self, amount, currency, invoice_id=None, description=None):
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


class StripeCard(StripeSource):
    """
    You can store multiple cards on a customer in order to charge the customer later.
    (Source: https://stripe.com/docs/api/python#cards)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:
    * object: Unnecessary. Just check the model name.
    * recipient: On Stripe's deprecation path.
    * account: #
    * currency: #
    * default_for_currency: #

    Stripe API_VERSION: model fields and methods audited to 2015-07-28 - @kavdev
    """

    BRANDS = ["Visa", "American Express", "MasterCard", "Discover", "JCB", "Diners Club", "Unknown"]
    BRAND_CHOICES = [(brand, brand) for brand in BRANDS]

    FUNDING_TYPES = ["credit", "debit", "prepaid", "unknown"]
    FUNDING_TYPE_CHOICES = [(funding_type, funding_type.title()) for funding_type in FUNDING_TYPES]

    CARD_CHECK_RESULTS = ["pass", "fail", "unavailable", "unknown"]
    CARD_CHECK_RESULT_CHOICES = [(card_check_result, card_check_result.title()) for card_check_result in CARD_CHECK_RESULTS]

    TOKENIZATION_METHODS = ["apple_pay", "android_pay"]
    TOKENIZATION_METHOD_CHOICES = [(tokenization_method, tokenization_method.replace("_", " ").title()) for tokenization_method in TOKENIZATION_METHODS]

    class Meta:
        abstract = True

    stripe_api_name = "Card"

    brand = StripeCharField(max_length=16, choices=BRAND_CHOICES, help_text="Card brand.")
    exp_month = StripeIntegerField(help_text="Card expiration month.")
    exp_year = StripeIntegerField(help_text="Card expiration year.")
    funding = StripeCharField(max_length=7, choices=FUNDING_TYPE_CHOICES, help_text="Card funding type.")
    last4 = StripeCharField(max_length=4, help_text="Last four digits of Card number.")

    address_city = StripeTextField(null=True, help_text="Billing address city.")
    address_country = StripeTextField(null=True, help_text="Billing address country.")
    address_line1 = StripeTextField(null=True, help_text="Billing address (Line 1).")
    address_line1_check = StripeCharField(null=True, max_length=11, choices=CARD_CHECK_RESULT_CHOICES, help_text="If ``address_line1`` was provided, results of the check.")
    address_line2 = StripeTextField(null=True, help_text="Billing address (Line 2).")
    address_state = StripeTextField(null=True, help_text="Billing address state.")
    address_zip = StripeTextField(null=True, help_text="Billing address zip code.")
    address_zip_check = StripeCharField(null=True, max_length=11, choices=CARD_CHECK_RESULT_CHOICES, help_text="If ``address_zip`` was provided, results of the check.")

    country = StripeCharField(max_length=2, help_text="Two-letter ISO code representing the country of the card.")
    cvc_check = StripeCharField(null=True, max_length=11, choices=CARD_CHECK_RESULT_CHOICES, help_text="If a CVC was provided, results of the check.")
    dynamic_last4 = StripeCharField(null=True, max_length=4, help_text="(For tokenized numbers only.) The last four digits of the device account number.")
    name = StripeTextField(null=True, help_text="Cardholder name.")
    tokenization_method = StripeCharField(null=True, max_length=11, choices=TOKENIZATION_METHOD_CHOICES, help_text="If the card number is tokenized, this is the method that was used.")
    fingerprint = StripeTextField(stripe_required=False, help_text="Uniquely identifies this particular card number.")

    # TODO: See if accepting a customer/account in the create call is reasonable.

    @classmethod
    def _api(cls):
        raise StripeObjectManipulationException("Cards must be manipulated through either a customer or an account.")

    def api_retrieve(self, api_key=settings.STRIPE_SECRET_KEY):
        # OVERRIDING the parent version of this function
        # Cards must be manipulated through a customer or account.

        # TODO: When managed accounts are supported, this method needs to check if either a customer or account is supplied to determine the correct object to use.
        return self.customer.api_retrieve().sources.retrieve(id=self.stripe_id, api_key=api_key, expand=self.expand_fields)

    def str_parts(self):
        return [
            "brand={brand}".format(brand=self.brand),
            "last4={last4}".format(last4=self.last4),
            "exp_month={exp_month}".format(exp_month=self.exp_month),
            "exp_year={exp_year}".format(exp_year=self.exp_year),
        ] + super(StripeCard, self).str_parts()

    @classmethod
    def stripe_object_to_account(cls, target_cls, data):
        """
        Search the given manager for the Account matching this StripeCharge object's ``account`` field.

        :param target_cls: The target class
        :type target_cls: StripeAccount
        :param data: stripe object
        :type data: dict
        """

        if "account" in data and data["account"]:
            return target_cls.get_or_create_from_stripe_object(data, "account")[0]


class StripeSubscription(StripeObject):
    """
    Subscriptions allow you to charge a customer's card on a recurring basis. A subscription ties a customer to a particular plan you've created.
    (Source: https://stripe.com/docs/api/python#subscriptions)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:
    * object: Unnecessary. Just check the model name.
    * application_fee_percent: #
    * discount: #

    Stripe API_VERSION: model fields and methods audited to 2015-07-28 - @kavdev
    """

    class Meta:
        abstract = True

    stripe_api_name = "Subscription"

    STATUS_ACTIVE = "active"
    STATUS_TRIALING = "trialing"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELLED = "canceled"
    STATUS_UNPAID = "unpaid"

    STATUSES = [STATUS_TRIALING, STATUS_ACTIVE, STATUS_PAST_DUE, STATUS_CANCELLED, STATUS_UNPAID]
    STATUS_CHOICES = [(status, status.replace("_", " ").title()) for status in STATUSES]

    cancel_at_period_end = StripeBooleanField(default=False, help_text="If the subscription has been canceled with the ``at_period_end`` flag set to true, ``cancel_at_period_end`` on the subscription will be true. You can use this attribute to determine whether a subscription that has a status of active is scheduled to be canceled at the end of the current period.")
    quantity = StripeIntegerField(help_text="The quantity applied to this subscription.")
    start = StripeDateTimeField(help_text="Date the subscription started.")
    status = StripeCharField(max_length=8, choices=STATUS_CHOICES, help_text="The status of this subscription.")
    canceled_at = StripeDateTimeField(null=True, help_text="If the subscription has been canceled, the date of that cancellation.")
    current_period_end = StripeDateTimeField(help_text="End of the current period for which the subscription has been invoiced. At the end of this period, a new invoice will be created.")
    current_period_start = StripeDateTimeField(help_text="Start of the current period for which the subscription has been invoiced.")
    ended_at = StripeDateTimeField(null=True, help_text="If the subscription has ended (either because it was canceled or because the customer was switched to a subscription to a new plan), the date the subscription ended.")
    tax_percent = StripePercentField(null=True, help_text="A positive decimal (with at most two decimal places) between 1 and 100. This represents the percentage of the subscription invoice subtotal that will be calculated and added as tax to the final amount each billing period.")
    trial_end = StripeDateTimeField(null=True, help_text="If the subscription has a trial, the end of that trial.")
    trial_start = StripeDateTimeField(null=True, help_text="If the subscription has a trial, the beginning of that trial.")

    # TODO: See if accepting a customer/account in the create call is reasonable.

    @classmethod
    def _api(cls):
        raise StripeObjectManipulationException("Subscriptions must be manipulated through either a customer.")

    def api_retrieve(self, api_key=settings.STRIPE_SECRET_KEY):
        # OVERRIDING the parent version of this function
        # Subscriptions must be manipulated through a customer.

        return self.customer.api_retrieve().subscriptions.retrieve(id=self.stripe_id, api_key=api_key, expand=self.expand_fields)

    def str_parts(self):
        return [
            "current_period_start={current_period_start}".format(current_period_start=self.current_period_start),
            "current_period_end={current_period_end}".format(current_period_end=self.current_period_end),
            "status={status}".format(status=self.status),
            "quantity={quantity}".format(quantity=self.quantity),
        ] + super(StripeSubscription, self).str_parts()

    @classmethod
    def stripe_object_to_plan(cls, target_cls, data):
        """
        Search the given manager for the Plan matching this StripeCharge object's ``plan`` field.

        :param target_cls: The target class
        :type target_cls: StripePlan
        :param data: stripe object
        :type data: dict
        """

        return target_cls.get_or_create_from_stripe_object(data["plan"])[0]

    def update(self, plan=None, coupon=None, prorate=None, proration_date=None, trial_end=None, quantity=None, application_fee_percent=None, tax_percent=None, metadata=None):
        """
        See StripeCustomer.subscribe()

        :param prorate: Whether or not to prorate when switching plans. Default is True.
        :type prorate: boolean
        :param proration_date: If set, the proration will be calculated as though the subscription was updated at the given time.
                               This can be used to apply exactly the same proration that was previewed with upcoming invoice endpoint.
                               It can also be used to implement custom proration logic, such as prorating by day instead of by second,
                               by providing the time that you wish to use for proration calculations.
        :type proration_date: datetime
        """

        kwargs = deepcopy(locals())
        del kwargs["self"]

        stripe_subscription = self.api_retrieve()

        for kwarg, value in kwargs.items():
            if value:
                setattr(stripe_subscription, kwarg, value)

        return stripe_subscription.save()

    def extend(self, delta):
        """
        Extends this subscription by the provided delta.

        :param delta: The timedelta by which to extend this subscription.
        :type delta: timedelta

        """

        if delta.total_seconds() < 0:
            raise ValueError("delta must be a positive timedelta.")

        period_end = None

        if self.trial_end is not None and self.trial_end > timezone.now():
            period_end = self.trial_end
        else:
            period_end = self.current_period_end

        period_end += delta

        stripe_subscription = self.api_retrieve()
        stripe_subscription.prorate = False
        stripe_subscription.trial_end = period_end
        stripe_subscription.save()

        return stripe_subscription

    def cancel(self, at_period_end=None):
        """
        Cancels this subscription. If you set the at_period_end parameter to true, the subscription will remain active until the end of the period,
        at which point it will be canceled and not renewed. By default, the subscription is terminated immediately. In either case, the customer will not be
        charged again for the subscription. Note, however, that any pending invoice items that you’ve created will still be charged for at the end of the period
        unless manually deleted. If you’ve set the subscription to cancel at period end, any pending prorations will also be left in place and collected at the
        end of the period, but if the subscription is set to cancel immediately, pending prorations will be removed.

        By default, all unpaid invoices for the customer will be closed upon subscription cancellation. We do this in order to prevent unexpected payment retries
        once the customer has canceled a subscription. However, you can reopen the invoices manually after subscription cancellation to have us proceed with automatic
        retries, or you could even re-attempt payment yourself on all unpaid invoices before allowing the customer to cancel the subscription at all.

        :param at_period_end: A flag that if set to true will delay the cancellation of the subscription until the end of the current period. Default is False.
        :type at_period_end: boolean

        """

        return self._api_delete(at_period_end)


class StripePlan(StripeObject):
    """
    A subscription plan contains the pricing information for different products and feature levels on your site.
    (Source: https://stripe.com/docs/api/python#plans)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:
    * object: Unnecessary. Just check the model name.

    Stripe API_VERSION: model fields and methods audited to 2015-07-28 - @kavdev
    """

    class Meta:
        abstract = True

    stripe_api_name = "Plan"

    INTERVAL_TYPES = ["day", "week", "month", "year"]
    INTERVAL_TYPE_CHOICES = [(interval_type, interval_type.title()) for interval_type in INTERVAL_TYPES]

    amount = StripeCurrencyField(help_text="Amount to be charged on the interval specified.")
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code")
    interval = StripeCharField(max_length=5, choices=INTERVAL_TYPE_CHOICES, help_text="The frequency with which a subscription should be billed.")
    interval_count = StripeIntegerField(null=True, help_text="The number of intervals (specified in the interval property) between each subscription billing.")
    name = StripeTextField(help_text="Name of the plan, to be displayed on invoices and in the web interface.")
    statement_descriptor = StripeCharField(max_length=22, null=True, help_text="An arbitrary string to be displayed on your customer’s credit card statement. The statement description may not include <>\"' characters, and will appear on your customer’s statement in capital letters. Non-ASCII characters are automatically stripped. While most banks display this information consistently, some may display it incorrectly or not at all.")
    trial_period_days = StripeIntegerField(null=True, help_text="Number of trial period days granted when subscribing a customer to this plan. Null if the plan has no trial period.")

    def str_parts(self):
        return [
            "name={name}".format(name=self.name),
        ] + super(StripePlan, self).str_parts()


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
    """
    When Stripe sends you money or you initiate a transfer to a bank account, debit card, or connected Stripe account, a transfer object will be created.
    (Source: https://stripe.com/docs/api/python#transfers)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:
    * object: Unnecessary. Just check the model name.

    TODO: Link destination to Card, Account, or Bank Account Models

    Stripe API_VERSION: model fields and methods audited to 2015-07-28 - @kavdev
    """

    class Meta:
        abstract = True

    stripe_api_name = "Transfer"
    expand_fields = ["balance_transaction"]

    STATUS_PAID = "paid"
    STATUS_PENDING = "pending"
    STATUS_IN_TRANSIT = "in_transit"
    STATUS_CANCELLED = "canceled"
    STATUS_FAILED = "failed"

    STATUSES = [STATUS_PAID, STATUS_PENDING, STATUS_IN_TRANSIT, STATUS_CANCELLED, STATUS_FAILED]
    STATUS_CHOICES = [(status, status.replace("_", " ").title()) for status in STATUSES]

    DESTINATION_TYPES = ["card", "bank_account", "stripe_account"]
    DESITNATION_TYPE_CHOICES = [(destination_type, destination_type.replace("_", " ").title()) for destination_type in DESTINATION_TYPES]

    FAILURE_CODES = ["insufficient_funds", "account_closed", "no_account", "invalid_account_number",
                     "debit_not_authorized", "bank_ownership_changed", "account_frozen", "could_not_process",
                     "bank_account_restricted", "invalid_currency"]
    FAILURE_CODE_CHOICES = [(failure_code, failure_code.replace("_", " ").title()) for failure_code in FAILURE_CODES]

    amount = StripeCurrencyField(help_text="The amount transferred")
    amount_reversed = StripeCurrencyField(stripe_required=False, help_text="The amount reversed (can be less than the amount attribute on the transfer if a partial reversal was issued).")
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code")
    date = StripeDateTimeField(help_text="Date the transfer is scheduled to arrive in the bank. This doesn’t factor in delays like weekends or bank holidays.")
    reversals = StripeJSONField(help_text="A list of reversals that have been applied to the transfer.")
    reversed = StripeBooleanField(default=False, help_text="Whether or not the transfer has been fully reversed. If the transfer is only partially reversed, this attribute will still be false.")
    status = StripeCharField(max_length=10, choices=STATUS_CHOICES, help_text="The current status of the transfer. A transfer will be pending until it is submitted to the bank, at which point it becomes in_transit. It will then change to paid if the transaction goes through. If it does not go through successfully, its status will change to failed or canceled.")
    destination_type = StripeCharField(stripe_name="type", max_length=14, choices=DESITNATION_TYPE_CHOICES, help_text="The type of the transfer destination.")
    application_fee = StripeTextField(null=True, help_text="Might be the ID of an application fee object. The Stripe API docs don't provide any information.")
    destination = StripeIdField(help_text="ID of the bank account, card, or Stripe account the transfer was sent to.")
    destination_payment = StripeIdField(stripe_required=False, help_text="If the destination is a Stripe account, this will be the ID of the payment that the destination account received for the transfer.")
    failure_code = StripeCharField(null=True, max_length=23, choices=FAILURE_CODE_CHOICES, help_text="Error code explaining reason for transfer failure if available. See https://stripe.com/docs/api/python#transfer_failures.")
    failure_message = StripeTextField(null=True, help_text="Message to user further explaining reason for transfer failure if available.")
    source_transaction = StripeIdField(null=True, help_text="ID of the charge (or other transaction) that was used to fund the transfer. If null, the transfer was funded from the available balance.")
    statement_descriptor = StripeCharField(max_length=22, null=True, help_text="An arbitrary string to be displayed on your customer’s credit card statement. The statement description may not include <>\"' characters, and will appear on your customer’s statement in capital letters. Non-ASCII characters are automatically stripped. While most banks display this information consistently, some may display it incorrectly or not at all.")

    fee_details = StripeJSONField(null=True, nested_name="balance_transaction")

    # DEPRECATED Fields
    adjustment_count = StripeIntegerField(deprecated=True)
    adjustment_fees = StripeCurrencyField(deprecated=True)
    adjustment_gross = StripeCurrencyField(deprecated=True)
    charge_count = StripeIntegerField(deprecated=True)
    charge_fees = StripeCurrencyField(deprecated=True)
    charge_gross = StripeCurrencyField(deprecated=True)
    collected_fee_count = StripeIntegerField(deprecated=True)
    collected_fee_gross = StripeCurrencyField(deprecated=True)
    net = StripeCurrencyField(deprecated=True)
    refund_count = StripeIntegerField(deprecated=True)
    refund_fees = StripeCurrencyField(deprecated=True)
    refund_gross = StripeCurrencyField(deprecated=True)
    validation_count = StripeIntegerField(deprecated=True)
    validation_fees = StripeCurrencyField(deprecated=True)

    def str_parts(self):
        return [
            "amount={amount}".format(amount=self.amount),
            "status={status}".format(status=self.status),
        ] + super(StripeTransfer, self).str_parts()


class StripeAccount(StripeObject):

    class Meta:
        abstract = True

    stripe_api_name = "Account"

    # Account -- add_card(external_account);

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
