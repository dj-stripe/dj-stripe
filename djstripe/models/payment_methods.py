from typing import Optional, Union

import stripe
from django.db import models, transaction
from stripe import InvalidRequestError

from .. import enums
from ..exceptions import ImpossibleAPIRequest, StripeObjectManipulationException
from ..fields import (
    JSONField,
    StripeCurrencyCodeField,
    StripeDecimalCurrencyAmountField,
    StripeEnumField,
    StripeForeignKey,
)
from ..settings import djstripe_settings
from ..utils import get_id_from_stripe_data
from .account import Account
from .base import StripeModel, logger
from .core import Customer


class DjstripePaymentMethod(models.Model):
    """
    An internal model that abstracts the legacy Card and BankAccount
    objects with Source objects.

    Contains two fields: `id` and `type`:
    - `id` is the id of the Stripe object.
    - `type` can be `card`, `bank_account` `account` or `source`.
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
    def _get_or_create_source(
        cls, data, source_type=None, api_key=djstripe_settings.STRIPE_SECRET_KEY
    ):
        # prefer passed in source_type
        if not source_type:
            source_type = data["object"]

        try:
            model = cls._model_for_type(source_type)
            model._get_or_create_from_stripe_object(data, api_key=api_key)
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
        elif type == "account":
            return Account

        raise ValueError(f"Unknown source type: {type}")

    @property
    def object_model(self):
        return self._model_for_type(self.type)

    def resolve(self):
        return self.object_model.objects.get(id=self.id)

    @classmethod
    def _get_or_create_from_stripe_object(
        cls,
        data,
        field_name="id",
        refetch=True,
        current_ids=None,
        pending_relations=None,
        save=True,
        stripe_account=None,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
    ):
        raw_field_data = data.get(field_name)
        id_ = get_id_from_stripe_data(raw_field_data)
        if not id_:
            raise ValueError(f"ID not found in Stripe data: {raw_field_data!r}")

        if id_.startswith("card"):
            source_cls = Card
            source_type = "card"
        elif id_.startswith("src"):
            source_cls = Source
            source_type = "source"
        elif id_.startswith("ba"):
            source_cls = BankAccount
            source_type = "bank_account"
        elif id_.startswith("acct"):
            source_cls = Account
            source_type = "account"
        else:
            # This may happen if we have source types we don't know about.
            # Let's not make dj-stripe entirely unusable if that happens.
            logger.warning(f"Unknown Object. Could not sync source with id: {id_}")
            return cls.objects.get_or_create(
                id=id_, defaults={"type": f"UNSUPPORTED_{id_}"}
            )

        # call model's _get_or_create_from_stripe_object to ensure
        # that object exists before getting or creating its source object
        source_cls._get_or_create_from_stripe_object(
            data,
            field_name,
            refetch=refetch,
            current_ids=current_ids,
            pending_relations=pending_relations,
            stripe_account=stripe_account,
            api_key=api_key,
        )

        return cls.objects.get_or_create(id=id_, defaults={"type": source_type})


class LegacySourceMixin:
    """
    Mixin for functionality shared between the legacy Card & BankAccount sources
    """

    customer: Optional[StripeForeignKey]
    account: Optional[StripeForeignKey]
    id: str
    default_api_key: str

    @classmethod
    def _get_customer_or_account_from_kwargs(cls, **kwargs):
        account = kwargs.get("account")
        customer = kwargs.get("customer")

        if not account and not customer:
            raise StripeObjectManipulationException(
                f"{cls.__name__} objects must be manipulated through either a "
                "Stripe Connected Account or a customer. "
                "Pass a Customer or an Account object into this call."
            )

        if account and not isinstance(account, Account):
            raise StripeObjectManipulationException(
                f"{cls.__name__} objects must be manipulated through a Stripe Connected"
                " Account. Pass an Account object into this call."
            )

        if customer and not isinstance(customer, Customer):
            raise StripeObjectManipulationException(
                f"{cls.__name__} objects must be manipulated through a Customer. "
                "Pass a Customer object into this call."
            )

        if account:
            del kwargs["account"]
        if customer:
            del kwargs["customer"]

        return account, customer, kwargs

    @classmethod
    def _api_create(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        # OVERRIDING the parent version of this function
        # Cards & Bank Accounts must be manipulated through a customer or account.

        account, customer, clean_kwargs = cls._get_customer_or_account_from_kwargs(
            **kwargs
        )

        # First we try to retrieve by customer attribute,
        # then by account attribute
        if customer and account:
            try:
                # retrieve by customer
                return customer.api_retrieve(api_key=api_key).sources.create(
                    api_key=api_key, **clean_kwargs
                )
            except Exception as customer_exc:
                try:
                    # retrieve by account
                    return account.api_retrieve(
                        api_key=api_key
                    ).external_accounts.create(api_key=api_key, **clean_kwargs)
                except Exception:
                    raise customer_exc

        if customer:
            return customer.api_retrieve(api_key=api_key).sources.create(
                api_key=api_key, **clean_kwargs
            )

        if account:
            return account.api_retrieve(api_key=api_key).external_accounts.create(
                api_key=api_key, **clean_kwargs
            )

    @classmethod
    def api_list(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        # OVERRIDING the parent version of this function
        # Cards & Bank Accounts must be manipulated through a customer or account.

        # Update kwargs with `expand` param
        kwargs = cls.get_expand_params(api_key, **kwargs)

        account, customer, clean_kwargs = cls._get_customer_or_account_from_kwargs(
            **kwargs
        )

        object_name = cls.stripe_class.OBJECT_NAME

        # First we try to retrieve by customer attribute,
        # then by account attribute
        if customer and account:
            try:
                # retrieve by customer
                return (
                    customer.api_retrieve(api_key=api_key)
                    .sources.list(object=object_name, **clean_kwargs)
                    .auto_paging_iter()
                )
            except Exception as customer_exc:
                try:
                    # retrieve by account
                    return (
                        account.api_retrieve(api_key=api_key)
                        .external_accounts.list(object=object_name, **clean_kwargs)
                        .auto_paging_iter()
                    )
                except Exception:
                    raise customer_exc

        if customer:
            return (
                customer.api_retrieve(api_key=api_key)
                .sources.list(object=object_name, **clean_kwargs)
                .auto_paging_iter()
            )

        if account:
            return (
                account.api_retrieve(api_key=api_key)
                .external_accounts.list(object=object_name, **clean_kwargs)
                .auto_paging_iter()
            )

        raise ImpossibleAPIRequest(
            f"Can't list {object_name} without a customer or account object. This may"
            " happen if not all accounts or customer objects are in the db. Please run"
            ' "python manage.py djstripe_sync_models Account Customer" as a potential'
            " fix."
        )

    def get_stripe_dashboard_url(self) -> str:
        if self.customer:
            return self.customer.get_stripe_dashboard_url()
        elif self.account:
            return f"https://dashboard.stripe.com/{self.account.id}/settings/payouts"
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

        api_key = api_key or self.default_api_key

        if self.customer:
            return stripe.Customer.retrieve_source(
                self.customer.id,
                self.id,
                expand=self.expand_fields,
                stripe_account=stripe_account,
                api_key=api_key,
                stripe_version=djstripe_settings.STRIPE_API_VERSION,
            )

        # try to retrieve by account attribute if retrieval by customer fails.
        if self.account:
            return stripe.Account.retrieve_external_account(
                self.account.id,
                self.id,
                expand=self.expand_fields,
                stripe_account=stripe_account,
                api_key=api_key,
                stripe_version=djstripe_settings.STRIPE_API_VERSION,
            )

        raise ImpossibleAPIRequest(
            f"Can't retrieve {self.__class__} without a customer or account object."
            " This may happen if not all accounts or customer objects are in the db."
            ' Please run "python manage.py djstripe_sync_models Account Customer" as a'
            " potential fix."
        )

    def _api_delete(self, api_key=None, stripe_account=None, **kwargs):
        # OVERRIDING the parent version of this function
        # Cards & Banks Accounts must be manipulated through a customer or account.

        api_key = api_key or self.default_api_key
        # Prefer passed in stripe_account if set.
        if not stripe_account:
            stripe_account = self._get_stripe_account_id(api_key)

        if self.customer:
            return stripe.Customer.delete_source(
                self.customer.id,
                self.id,
                api_key=api_key,
                stripe_account=stripe_account,
                **kwargs,
            )

        if self.account:
            return stripe.Account.delete_external_account(
                self.account.id,
                self.id,
                api_key=api_key,
                stripe_account=stripe_account,
                **kwargs,
            )

        raise ImpossibleAPIRequest(
            f"Can't delete {self.__class__} without a customer or account object. This"
            " may happen if not all accounts or customer objects are in the db. Please"
            ' run "python manage.py djstripe_sync_models Account Customer" as a'
            " potential fix."
        )


class BankAccount(LegacySourceMixin, StripeModel):
    """
    These bank accounts are payment methods on Customer objects.
    On the other hand External Accounts are transfer destinations on Account
    objects for Custom accounts. They can be bank accounts or debit cards as well.

    Stripe documentation:https://stripe.com/docs/api/customer_bank_accounts
    """

    stripe_class = stripe.BankAccount

    account = StripeForeignKey(
        "Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bank_accounts",
        help_text=(
            "The external account the charge was made on behalf of. Null here indicates"
            " that this value was never set."
        ),
    )
    customer = StripeForeignKey(
        "Customer", on_delete=models.SET_NULL, null=True, related_name="bank_account"
    )
    fingerprint = models.CharField(
        max_length=16,
        help_text=(
            "Uniquely identifies this particular bank account. "
            "You can use this attribute to check whether two bank accounts are "
            "the same."
        ),
    )

    @property
    def account_holder_name(self):
        return self.stripe_data.get("account_holder_name")

    @property
    def account_holder_type(self):
        return self.stripe_data.get("account_holder_type")

    @property
    def bank_name(self):
        return self.stripe_data.get("bank_name")

    @property
    def country(self):
        return self.stripe_data.get("country")

    @property
    def currency(self):
        return self.stripe_data.get("currency")

    @property
    def default_for_currency(self):
        return self.stripe_data.get("default_for_currency")

    @property
    def last4(self):
        return self.stripe_data.get("last4")

    @property
    def routing_number(self):
        return self.stripe_data.get("routing_number")

    @property
    def status(self):
        return self.stripe_data.get("status")

    def __str__(self):
        default = False
        # prefer to show it by customer format if present
        if self.customer:
            default_source = self.customer.default_source
            default_payment_method = self.customer.default_payment_method

            if (default_payment_method and self.id == default_payment_method.id) or (
                default_source and self.id == default_source.id
            ):
                # current card is the default payment method or source
                default = True

            customer_template = (
                f"{self.bank_name or ''} {self.routing_number or ''} ({self.human_readable_status})"
                f" {'Default' if default else ''} {self.currency or ''}"
            )
            return customer_template

        default = getattr(self, "default_for_currency", False)
        account_template = f"{self.bank_name or ''} {self.currency or ''} {'Default' if default else ''} {self.routing_number or ''} {self.last4 or ''}"
        return account_template

    @property
    def human_readable_status(self):
        if self.status == "new":
            return "Pending Verification"
        return enums.BankAccountStatus.humanize(self.status) if self.status else ""

    def api_retrieve(self, **kwargs):
        if not self.customer and not self.account:
            raise ImpossibleAPIRequest(
                "Can't retrieve a bank account without a customer or account object."
                " This may happen if not all accounts or customer objects are in the"
                ' db. Please run "python manage.py djstripe_sync_models Account'
                ' Customer" as a potential fix.'
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

    Stripe documentation: https://stripe.com/docs/api?lang=python#cards
    """

    stripe_class = stripe.Card
    # Stripe Custom Connected Accounts can have cards as "Payout Sources"
    account = StripeForeignKey(
        "Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cards",
        help_text=(
            "The external account the charge was made on behalf of. Null here indicates"
            " that this value was never set."
        ),
    )
    customer = StripeForeignKey(
        "Customer", on_delete=models.SET_NULL, null=True, related_name="legacy_cards"
    )
    fingerprint = models.CharField(
        default="",
        blank=True,
        max_length=16,
        help_text="Uniquely identifies this particular card number.",
    )

    @property
    def address_city(self):
        return self.stripe_data.get("address_city")

    @property
    def address_country(self):
        return self.stripe_data.get("address_country")

    @property
    def address_line1(self):
        return self.stripe_data.get("address_line1")

    @property
    def address_line1_check(self):
        return self.stripe_data.get("address_line1_check")

    @property
    def address_line2(self):
        return self.stripe_data.get("address_line2")

    @property
    def address_state(self):
        return self.stripe_data.get("address_state")

    @property
    def address_zip(self):
        return self.stripe_data.get("address_zip")

    @property
    def address_zip_check(self):
        return self.stripe_data.get("address_zip_check")

    @property
    def brand(self):
        return self.stripe_data.get("brand")

    @property
    def country(self):
        return self.stripe_data.get("country")

    @property
    def cvc_check(self):
        return self.stripe_data.get("cvc_check")

    @property
    def default_for_currency(self):
        return self.stripe_data.get("default_for_currency")

    @property
    def dynamic_last4(self):
        return self.stripe_data.get("dynamic_last4")

    @property
    def exp_month(self):
        return self.stripe_data.get("exp_month")

    @property
    def exp_year(self):
        return self.stripe_data.get("exp_year")

    @property
    def funding(self):
        return self.stripe_data.get("funding")

    @property
    def last4(self):
        return self.stripe_data.get("last4")

    @property
    def name(self):
        return self.stripe_data.get("name")

    @property
    def tokenization_method(self):
        return self.stripe_data.get("tokenization_method")

    def __str__(self):
        default = False
        # prefer to show it by customer format if present
        if self.customer:
            default_source = self.customer.default_source
            default_payment_method = self.customer.default_payment_method

            if (default_payment_method and self.id == default_payment_method.id) or (
                default_source and self.id == default_source.id
            ):
                # current card is the default payment method or source
                default = True

            customer_template = (
                f"{enums.CardBrand.humanize(self.brand) if self.brand else ''} {self.last4 or ''} {'Default' if default else ''} Expires"
                f" {self.exp_month or ''} {self.exp_year or ''}"
            )
            return customer_template

        elif self.account:
            default = getattr(self, "default_for_currency", False)
            account_template = f"{enums.CardBrand.humanize(self.brand) if self.brand else ''} {self.account.default_currency} {'Default' if default else ''} {self.last4 or ''}"
            return account_template

        return self.id or ""

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
        (Source: https://stripe.com/docs/api?lang=python#create_card_token)

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
    Source objects allow you to accept a variety of payment methods.
    They represent a customer's payment instrument, and can be used with
    the Stripe API just like a Card object: once chargeable,
    they can be charged, or can be attached to customers.

    Stripe documentation: https://stripe.com/docs/api?lang=python#sources
    """

    customer = StripeForeignKey(
        "Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sources",
    )

    stripe_class = stripe.Source
    stripe_dashboard_item_name = "sources"

    @property
    def amount(self):
        return self.stripe_data.get("amount")

    @property
    def client_secret(self):
        return self.stripe_data.get("client_secret")

    @property
    def currency(self):
        return self.stripe_data.get("currency")

    @property
    def flow(self):
        return self.stripe_data.get("flow")

    @property
    def owner(self):
        return self.stripe_data.get("owner")

    @property
    def statement_descriptor(self):
        return self.stripe_data.get("statement_descriptor")

    @property
    def status(self):
        return self.stripe_data.get("status")

    @property
    def type(self):
        return self.stripe_data.get("type")

    @property
    def usage(self):
        return self.stripe_data.get("usage")

    @property
    def code_verification(self):
        return self.stripe_data.get("code_verification")

    @property
    def receiver(self):
        return self.stripe_data.get("receiver")

    @property
    def redirect(self):
        return self.stripe_data.get("redirect")

    @property
    def source_data(self):
        # The source_data dict is an alias of all the source types
        source_type = self.stripe_data.get("type")
        if source_type:
            return self.stripe_data.get(source_type, {})
        return {}

    def __str__(self):
        return f"{self.type or ''} {self.id}"

    def _attach_objects_hook(
        self, cls, data, api_key=djstripe_settings.STRIPE_SECRET_KEY, current_ids=None
    ):
        customer = None
        # "customer" key could be like "cus_6lsBvm5rJ0zyHc" or {"id": "cus_6lsBvm5rJ0zyHc"}
        customer_id = get_id_from_stripe_data(data.get("customer"))

        if current_ids is None or customer_id not in current_ids:
            customer = cls._stripe_object_to_customer(
                target_cls=Customer, data=data, current_ids=current_ids, api_key=api_key
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
        api_key = self.default_api_key
        try:
            # TODO - we could use the return value of sync_from_stripe_data
            #  or call its internals - self._sync/_attach_objects_hook etc here
            #  to update `self` at this point?
            self.sync_from_stripe_data(
                self.api_retrieve(api_key=api_key).detach(), api_key=api_key
            )
            return True
        except InvalidRequestError:
            # The source was already detached. Resyncing.
            self.sync_from_stripe_data(
                self.api_retrieve(api_key=self.default_api_key),
                api_key=self.default_api_key,
            )
            return False

    @classmethod
    def api_list(
        cls,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
        *,
        customer: Customer,
        **kwargs,
    ):
        """
        Call the stripe API's list operation for this model.
        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        See Stripe documentation for accepted kwargs for each object.
        :returns: an iterator over all items in the query
        """
        # Update kwargs with `expand` param
        kwargs = cls.get_expand_params(api_key, **kwargs)

        return Customer.stripe_class.list_sources(
            object="source",
            api_key=api_key,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
            customer=customer.id,
            **kwargs,
        ).auto_paging_iter()


class SourceTransaction(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/sources/ach-credit-transfer#source-transactions
    """

    stripe_class = stripe.SourceTransaction
    stripe_dashboard_item_name = "source_transactions"

    metadata = None
    type = enums.SourceType.ach_credit_transfer

    ach_credit_transfer = JSONField(
        help_text="The data corresponding to the ach_credit_transfer type."
    )
    amount = StripeDecimalCurrencyAmountField(
        null=True,
        blank=True,
        help_text=(
            "Amount (as decimal) associated with the ACH Credit Transfer. This is the"
            " amount your customer has sent for which the source will be chargeable"
            " once ready. "
        ),
    )
    currency = StripeCurrencyCodeField()

    # did not use CharField because no idea about possible max-length
    customer_data = JSONField(
        null=True,
        blank=True,
        help_text="Customer defined string used to initiate the ACH Credit Transfer.",
    )
    # source cannot be null but we are allowing this because the order of webhooks is not deterministic
    source = StripeForeignKey(
        "Source",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status = StripeEnumField(
        enum=enums.SourceTransactionStatus,
        help_text=(
            "The status of the ACH Credit Transfer. Only `chargeable` sources can be"
            " used to create a charge."
        ),
    )

    def __str__(self):
        return f"Source Transaction status={self.status}, source={self.source.id}"

    @classmethod
    def api_list(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        """
        Call the stripe API's list operation for this model.
        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        See Stripe documentation for accepted kwargs for each object.
        :returns: an iterator over all items in the query
        """
        # Update kwargs with `expand` param
        kwargs = cls.get_expand_params(api_key, **kwargs)

        source = kwargs.pop("id", None)
        if not source:
            raise KeyError("Source Object ID is missing")

        return stripe.Source.list_source_transactions(
            source, api_key=api_key, **kwargs
        ).auto_paging_iter()

    def api_retrieve(self, api_key=None, stripe_account=None):
        """
        Call the stripe API's retrieve operation for this model.

        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        """
        # Prefer passed in stripe_account if set.
        if not stripe_account:
            stripe_account = self._get_stripe_account_id(api_key)

        for source_trx in SourceTransaction.api_list(
            id=self.source.id, api_key=api_key, stripe_account=stripe_account
        ):
            if source_trx.id == self.id:
                return source_trx

    def get_stripe_dashboard_url(self) -> str:
        """Get the stripe dashboard url for this object."""
        if (
            not self.stripe_dashboard_item_name
            or not self.id
            or not self.source
            or not self.source.id
        ):
            return ""
        return f"{self._get_base_stripe_dashboard_url()}sources/{self.source.id}"


class PaymentMethod(StripeModel):
    """
    PaymentMethod objects represent your customer's payment instruments.
    You can use them with PaymentIntents to collect payments or save them
    to Customer objects to store instrument details for future payments.

    Stripe documentation: https://stripe.com/docs/api?lang=python#payment_methods
    """

    stripe_class = stripe.PaymentMethod

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

    @property
    def type(self):
        return self.stripe_data.get("type")

    def get_stripe_dashboard_url(self) -> str:
        if self.customer:
            return self.customer.get_stripe_dashboard_url()
        return ""

    def _attach_objects_hook(
        self, cls, data, api_key=djstripe_settings.STRIPE_SECRET_KEY, current_ids=None
    ):
        customer = None
        # "customer" key could be like "cus_6lsBvm5rJ0zyHc" or {"id": "cus_6lsBvm5rJ0zyHc"}
        customer_id = get_id_from_stripe_data(data.get("customer"))

        if current_ids is None or customer_id not in current_ids:
            customer = cls._stripe_object_to_customer(
                target_cls=Customer, data=data, current_ids=current_ids, api_key=api_key
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
        return cls.sync_from_stripe_data(stripe_payment_method, api_key=api_key)

    @property
    def billing_details(self):
        return self.stripe_data.get("billing_details")

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
