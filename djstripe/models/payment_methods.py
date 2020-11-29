from typing import Optional, Union

import stripe
from django.db import models, transaction
from stripe.error import InvalidRequestError

from .. import enums
from .. import settings as djstripe_settings
from ..exceptions import StripeObjectManipulationException
from ..fields import (
    JSONField,
    StripeCurrencyCodeField,
    StripeDecimalCurrencyAmountField,
    StripeEnumField,
    StripeForeignKey,
)
from .base import StripeModel, logger
from .core import Customer


class DjstripePaymentMethod(models.Model):
    """
    An internal model that abstracts the legacy Card and BankAccount
    objects with Source objects.

    Contains two fields: `id` and `type`:
    - `id` is the id of the Stripe object.
    - `type` can be `card`, `bank_account` or `source`.
    """

    id = models.CharField(max_length=255, primary_key=True)
    type = models.CharField(max_length=50, db_index=True)

    @classmethod
    def from_stripe_object(cls, data):
        source_type = data["object"]
        model = cls._model_for_type(source_type)

        with transaction.atomic():
            model.sync_from_stripe_data(data)
            instance, _ = cls.objects.get_or_create(
                id=data["id"], defaults={"type": source_type}
            )

        return instance

    @classmethod
    def _get_or_create_source(cls, data, source_type):
        try:
            model = cls._model_for_type(source_type)
            model._get_or_create_from_stripe_object(data)
        except ValueError as e:
            # This may happen if we have source types we don't know about.
            # Let's not make dj-stripe entirely unusable if that happens.
            logger.warning("Could not sync source of type %r: %s", source_type, e)

        return cls.objects.get_or_create(id=data["id"], defaults={"type": source_type})

    @classmethod
    def _model_for_type(cls, type):
        if type == "card":
            return Card
        elif type == "source":
            return Source
        elif type == "bank_account":
            return BankAccount

        raise ValueError("Unknown source type: {}".format(type))

    @property
    def object_model(self):
        return self._model_for_type(self.type)

    def resolve(self):
        return self.object_model.objects.get(id=self.id)


class LegacySourceMixin:
    """
    Mixin for functionality shared between the legacy Card & BankAccount sources
    """

    customer: Optional[StripeForeignKey]

    @classmethod
    def _get_customer_from_kwargs(cls, **kwargs):
        if "customer" not in kwargs or not isinstance(kwargs["customer"], Customer):
            raise StripeObjectManipulationException(
                "{}s must be manipulated through a Customer. "
                "Pass a Customer object into this call.".format(cls.__name__)
            )

        customer = kwargs["customer"]
        del kwargs["customer"]

        return customer, kwargs

    @classmethod
    def _api_create(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        # OVERRIDING the parent version of this function
        # Cards & Bank Accounts must be manipulated through a customer or account.
        # TODO: When managed accounts are supported, this method needs to
        #     check if either a customer or account is supplied to determine
        #     the correct object to use.

        customer, clean_kwargs = cls._get_customer_from_kwargs(**kwargs)

        return customer.api_retrieve().sources.create(api_key=api_key, **clean_kwargs)

    @classmethod
    def api_list(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        # OVERRIDING the parent version of this function
        # Cards & Bank Accounts must be manipulated through a customer or account.
        # TODO: When managed accounts are supported, this method needs to
        #     check if either a customer or account is supplied to determine
        #     the correct object to use.

        customer, clean_kwargs = cls._get_customer_from_kwargs(**kwargs)

        return (
            customer.api_retrieve(api_key=api_key)
            .sources.list(object=cls.stripe_class.OBJECT_NAME, **clean_kwargs)
            .auto_paging_iter()
        )

    def get_stripe_dashboard_url(self) -> str:
        if self.customer:
            return self.customer.get_stripe_dashboard_url()
        else:
            return ""

    def remove(self):
        """
        Removes a legacy source from this customer's account.
        """

        # First, wipe default source on all customers that use this card.
        Customer.objects.filter(default_source=self.id).update(default_source=None)

        try:
            self._api_delete()
        except InvalidRequestError as exc:
            if "No such source:" in str(exc) or "No such customer:" in str(exc):
                # The exception was thrown because the stripe customer or card
                # was already deleted on the stripe side, ignore the exception
                pass
            else:
                # The exception was raised for another reason, re-raise it
                raise

        self.delete()

    def api_retrieve(self, api_key=None, stripe_account=None):
        # OVERRIDING the parent version of this function
        # Cards & Banks Accounts must be manipulated through a customer or account.
        # TODO: When managed accounts are supported, this method needs to check if
        # either a customer or account is supplied to determine the
        # correct object to use.
        api_key = api_key or self.default_api_key
        customer = self.customer.api_retrieve(
            api_key=api_key, stripe_account=stripe_account
        )

        # If the customer is deleted, the sources attribute will be absent.
        # eg. {"id": "cus_XXXXXXXX", "deleted": True}
        if "sources" not in customer:
            # We fake a native stripe InvalidRequestError so that it's caught
            # like an invalid ID error.
            raise InvalidRequestError(f"No such source: {self.id!r}", "id")

        # This will retrieve the source using the account ID where the customer resides,
        # so we don't have to pass `stripe_account`.
        return customer.sources.retrieve(self.id, expand=self.expand_fields)


class BankAccount(LegacySourceMixin, StripeModel):
    stripe_class = stripe.BankAccount

    account = StripeForeignKey(
        "Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bank_account",
        help_text="The account the charge was made on behalf of. Null here indicates "
        "that this value was never set.",
    )
    account_holder_name = models.TextField(
        max_length=5000,
        blank=True,
        help_text="The name of the person or business that owns the bank account.",
    )
    account_holder_type = StripeEnumField(
        enum=enums.BankAccountHolderType,
        help_text="The type of entity that holds the account.",
    )
    bank_name = models.CharField(
        max_length=255,
        help_text="Name of the bank associated with the routing number "
        "(e.g., `WELLS FARGO`).",
    )
    country = models.CharField(
        max_length=2,
        help_text="Two-letter ISO code representing the country the bank account "
        "is located in.",
    )
    currency = StripeCurrencyCodeField()
    customer = StripeForeignKey(
        "Customer", on_delete=models.SET_NULL, null=True, related_name="bank_account"
    )
    default_for_currency = models.BooleanField(
        null=True,
        help_text="Whether this external account is the default account for "
        "its currency.",
    )
    fingerprint = models.CharField(
        max_length=16,
        help_text=(
            "Uniquely identifies this particular bank account. "
            "You can use this attribute to check whether two bank accounts are "
            "the same."
        ),
    )
    last4 = models.CharField(max_length=4)
    routing_number = models.CharField(
        max_length=255, help_text="The routing transit number for the bank account."
    )
    status = StripeEnumField(enum=enums.BankAccountStatus)

    def api_retrieve(self, **kwargs):
        if not self.customer:
            raise NotImplementedError(
                "Cannot retrieve bank accounts not associated with a customer"
            )
        return super().api_retrieve(**kwargs)


class Card(LegacySourceMixin, StripeModel):
    """
    You can store multiple cards on a customer in order to charge the customer later.

    This is a legacy model which only applies to the "v2" Stripe API (eg. Checkout.js).
    You should strive to use the Stripe "v3" API (eg. Stripe Elements).
    Also see: https://stripe.com/docs/stripe-js/elements/migrating
    When using Elements, you will not be using Card objects. Instead, you will use
    Source objects.
    A Source object of type "card" is equivalent to a Card object. However, Card
    objects cannot be converted into Source objects by Stripe at this time.

    Stripe documentation: https://stripe.com/docs/api/python#cards
    """

    stripe_class = stripe.Card

    address_city = models.TextField(
        max_length=5000,
        blank=True,
        default="",
        help_text="City/District/Suburb/Town/Village.",
    )
    address_country = models.TextField(
        max_length=5000, blank=True, default="", help_text="Billing address country."
    )
    address_line1 = models.TextField(
        max_length=5000,
        blank=True,
        default="",
        help_text="Street address/PO Box/Company name.",
    )
    address_line1_check = StripeEnumField(
        enum=enums.CardCheckResult,
        blank=True,
        default="",
        help_text="If `address_line1` was provided, results of the check.",
    )
    address_line2 = models.TextField(
        max_length=5000,
        blank=True,
        default="",
        help_text="Apartment/Suite/Unit/Building.",
    )
    address_state = models.TextField(
        max_length=5000,
        blank=True,
        default="",
        help_text="State/County/Province/Region.",
    )
    address_zip = models.TextField(
        max_length=5000, blank=True, default="", help_text="ZIP or postal code."
    )
    address_zip_check = StripeEnumField(
        enum=enums.CardCheckResult,
        blank=True,
        default="",
        help_text="If `address_zip` was provided, results of the check.",
    )
    brand = StripeEnumField(enum=enums.CardBrand, help_text="Card brand.")
    country = models.CharField(
        max_length=2,
        default="",
        blank=True,
        help_text="Two-letter ISO code representing the country of the card.",
    )
    customer = StripeForeignKey(
        "Customer", on_delete=models.SET_NULL, null=True, related_name="legacy_cards"
    )
    cvc_check = StripeEnumField(
        enum=enums.CardCheckResult,
        default="",
        blank=True,
        help_text="If a CVC was provided, results of the check.",
    )
    dynamic_last4 = models.CharField(
        max_length=4,
        default="",
        blank=True,
        help_text="(For tokenized numbers only.) The last four digits of the device "
        "account number.",
    )
    exp_month = models.IntegerField(help_text="Card expiration month.")
    exp_year = models.IntegerField(help_text="Card expiration year.")
    fingerprint = models.CharField(
        default="",
        blank=True,
        max_length=16,
        help_text="Uniquely identifies this particular card number.",
    )
    funding = StripeEnumField(
        enum=enums.CardFundingType, help_text="Card funding type."
    )
    last4 = models.CharField(max_length=4, help_text="Last four digits of Card number.")
    name = models.TextField(
        max_length=5000, default="", blank=True, help_text="Cardholder name."
    )
    tokenization_method = StripeEnumField(
        enum=enums.CardTokenizationMethod,
        default="",
        blank=True,
        help_text="If the card number is tokenized, this is the method that was used.",
    )

    def str_parts(self):
        return [
            "brand={brand}".format(brand=self.brand),
            "last4={last4}".format(last4=self.last4),
            "exp_month={exp_month}".format(exp_month=self.exp_month),
            "exp_year={exp_year}".format(exp_year=self.exp_year),
        ] + super().str_parts()

    @classmethod
    def create_token(
        cls,
        number: str,
        exp_month: int,
        exp_year: int,
        cvc: str,
        api_key: str = djstripe_settings.STRIPE_SECRET_KEY,
        **kwargs,
    ) -> stripe.Token:
        """
        Creates a single use token that wraps the details of a credit card.
        This token can be used in place of a credit card dictionary with any API method.
        These tokens can only be used once: by creating a new charge object,
        or attaching them to a customer.
        (Source: https://stripe.com/docs/api/python#create_card_token)

        :param number: The card number without any separators (no spaces)
        :param exp_month: The card's expiration month. (two digits)
        :param exp_year: The card's expiration year. (four digits)
        :param cvc: Card security code.
        :param api_key: The API key to use
        """

        card = {
            "number": number,
            "exp_month": exp_month,
            "exp_year": exp_year,
            "cvc": cvc,
        }
        card.update(kwargs)

        return stripe.Token.create(api_key=api_key, card=card)


class Source(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/api#sources
    """

    amount = StripeDecimalCurrencyAmountField(
        null=True,
        blank=True,
        help_text=(
            "Amount (as decimal) associated with the source. "
            "This is the amount for which the source will be chargeable once ready. "
            "Required for `single_use` sources."
        ),
    )
    client_secret = models.CharField(
        max_length=255,
        help_text=(
            "The client secret of the source. "
            "Used for client-side retrieval using a publishable key."
        ),
    )
    currency = StripeCurrencyCodeField(default="", blank=True)
    flow = StripeEnumField(
        enum=enums.SourceFlow, help_text="The authentication flow of the source."
    )
    owner = JSONField(
        help_text=(
            "Information about the owner of the payment instrument that may be "
            "used or required by particular source types."
        )
    )
    statement_descriptor = models.CharField(
        max_length=255,
        default="",
        blank=True,
        help_text="Extra information about a source. This will appear on your "
        "customer's statement every time you charge the source.",
    )
    status = StripeEnumField(
        enum=enums.SourceStatus,
        help_text="The status of the source. Only `chargeable` sources can be used "
        "to create a charge.",
    )
    type = StripeEnumField(enum=enums.SourceType, help_text="The type of the source.")
    usage = StripeEnumField(
        enum=enums.SourceUsage,
        help_text="Whether this source should be reusable or not. "
        "Some source types may or may not be reusable by construction, "
        "while other may leave the option at creation.",
    )

    # Flows
    code_verification = JSONField(
        null=True,
        blank=True,
        help_text="Information related to the code verification flow. "
        "Present if the source is authenticated by a verification code "
        "(`flow` is `code_verification`).",
    )
    receiver = JSONField(
        null=True,
        blank=True,
        help_text="Information related to the receiver flow. "
        "Present if the source is a receiver (`flow` is `receiver`).",
    )
    redirect = JSONField(
        null=True,
        blank=True,
        help_text="Information related to the redirect flow. "
        "Present if the source is authenticated by a redirect (`flow` is `redirect`).",
    )

    source_data = JSONField(help_text="The data corresponding to the source type.")

    customer = StripeForeignKey(
        "Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sources",
    )

    stripe_class = stripe.Source
    stripe_dashboard_item_name = "sources"

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        # The source_data dict is an alias of all the source types
        data["source_data"] = data[data["type"]]
        return data

    def _attach_objects_hook(self, cls, data, current_ids=None):
        customer = cls._stripe_object_to_customer(
            target_cls=Customer, data=data, current_ids=current_ids
        )
        if customer:
            self.customer = customer
        else:
            self.customer = None

    def detach(self) -> bool:
        """
        Detach the source from its customer.
        """

        # First, wipe default source on all customers that use this.
        Customer.objects.filter(default_source=self.id).update(default_source=None)

        try:
            # TODO - we could use the return value of sync_from_stripe_data
            #  or call its internals - self._sync/_attach_objects_hook etc here
            #  to update `self` at this point?
            self.sync_from_stripe_data(self.api_retrieve().detach())
            return True
        except (InvalidRequestError, NotImplementedError):
            # The source was already detached. Resyncing.
            # NotImplementedError is an artifact of stripe-python<2.0
            # https://github.com/stripe/stripe-python/issues/376
            self.sync_from_stripe_data(self.api_retrieve())
            return False


class PaymentMethod(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/api#payment_methods
    """

    stripe_class = stripe.PaymentMethod
    description = None

    billing_details = JSONField(
        help_text=(
            "Billing information associated with the PaymentMethod that may be used or "
            "required by particular types of payment methods."
        )
    )
    customer = StripeForeignKey(
        "Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_methods",
        help_text=(
            "Customer to which this PaymentMethod is saved. "
            "This will not be set when the PaymentMethod has "
            "not been saved to a Customer."
        ),
    )
    type = StripeEnumField(
        enum=enums.PaymentMethodType,
        help_text="The type of the PaymentMethod.",
    )
    alipay = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `alipay`",
    )
    au_becs_debit = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `au_becs_debit`",
    )
    bacs_debit = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `bacs_debit`",
    )
    bancontact = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `bancontact`",
    )
    card = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `card`",
    )
    card_present = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `card_present`",
    )
    eps = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `eps`",
    )
    fpx = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `fpx`",
    )
    giropay = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `giropay`",
    )
    ideal = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `ideal`",
    )
    interac_present = JSONField(
        null=True,
        blank=True,
        help_text=(
            "Additional information for payment methods of type `interac_present`"
        ),
    )
    oxxo = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `oxxo`",
    )
    p24 = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `p24`",
    )
    sepa_debit = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `sepa_debit`",
    )
    sofort = JSONField(
        null=True,
        blank=True,
        help_text="Additional information for payment methods of type `sofort`",
    )

    def _attach_objects_hook(self, cls, data, current_ids=None):
        customer = None
        if current_ids is None or data.get("customer") not in current_ids:
            customer = cls._stripe_object_to_customer(
                target_cls=Customer, data=data, current_ids=current_ids
            )

        if customer:
            self.customer = customer
        else:
            self.customer = None

    @classmethod
    def attach(
        cls,
        payment_method: Union[str, "PaymentMethod"],
        customer: Union[str, Customer],
        api_key: str = djstripe_settings.STRIPE_SECRET_KEY,
    ) -> "PaymentMethod":
        """
        Attach a payment method to a customer
        """

        if isinstance(payment_method, StripeModel):
            payment_method = payment_method.id

        if isinstance(customer, StripeModel):
            customer = customer.id

        extra_kwargs = {}
        if not isinstance(payment_method, stripe.PaymentMethod):
            # send api_key if we're not passing in a Stripe object
            # avoids "Received unknown parameter: api_key" since api uses the
            # key cached in the Stripe object
            extra_kwargs = {"api_key": api_key}

        stripe_payment_method = stripe.PaymentMethod.attach(
            payment_method, customer=customer, **extra_kwargs
        )
        return cls.sync_from_stripe_data(stripe_payment_method)

    def detach(self):
        """
        Detach the payment method from its customer.

        :return: Returns true if the payment method was newly detached, \
                 false if it was already detached
        :rtype: bool
        """
        # Find customers that use this
        customers = Customer.objects.filter(default_payment_method=self).all()
        changed = True

        # special handling is needed for legacy "card"-type PaymentMethods,
        # since detaching them deletes them within Stripe.
        # see https://github.com/dj-stripe/dj-stripe/pull/967
        is_legacy_card = self.id.startswith("card_")

        try:
            self.sync_from_stripe_data(self.api_retrieve().detach())

            # resync customer to update .default_payment_method and
            # .invoice_settings.default_payment_method
            for customer in customers:
                Customer.sync_from_stripe_data(customer.api_retrieve())

        except (InvalidRequestError,):
            # The source was already detached. Resyncing.

            if self.pk and not is_legacy_card:
                self.sync_from_stripe_data(self.api_retrieve())
            changed = False

        if self.pk:
            if is_legacy_card:
                self.delete()
            else:
                self.refresh_from_db()

        return changed
