from decimal import Decimal
from typing import Optional, Union

import stripe
from django.apps import apps
from django.db import models, transaction
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from stripe import InvalidRequestError

from .. import enums
from ..exceptions import MultipleSubscriptionException
from ..fields import (
    JSONField,
    PaymentMethodForeignKey,
    StripeCurrencyCodeField,
    StripeDecimalCurrencyAmountField,
    StripeEnumField,
    StripeForeignKey,
    StripeIdField,
    StripeQuantumCurrencyAmountField,
)
from ..managers import ChargeManager
from ..settings import djstripe_settings
from ..signals import WEBHOOK_SIGNALS
from ..utils import get_friendly_currency_amount, get_id_from_stripe_data
from .base import IdempotencyKey, StripeModel, logger


class BalanceTransaction(StripeModel):
    """
    A single transaction that updates the Stripe balance.

    Stripe documentation: https://stripe.com/docs/api?lang=python#balance_transaction_object
    """

    stripe_class = stripe.BalanceTransaction

    # Critical fields to keep
    amount = StripeQuantumCurrencyAmountField(
        help_text="Gross amount of the transaction, in cents."
    )
    currency = StripeCurrencyCodeField()
    source = StripeIdField()
    type = StripeEnumField(enum=enums.BalanceTransactionType)

    # Property accessors for commonly used fields
    @property
    def available_on(self):
        return self.stripe_data.get("available_on")

    @property
    def exchange_rate(self):
        return self.stripe_data.get("exchange_rate")

    @property
    def fee(self):
        return self.stripe_data.get("fee")

    @property
    def fee_details(self):
        return self.stripe_data.get("fee_details")

    @property
    def net(self):
        return self.stripe_data.get("net")

    @property
    def reporting_category(self):
        return self.stripe_data.get("reporting_category")

    @property
    def status(self):
        return self.stripe_data.get("status")

    def __str__(self):
        amount = get_friendly_currency_amount(self.amount / 100, self.currency)
        status = self.stripe_data.get("status", "unknown")
        if hasattr(enums.BalanceTransactionStatus, "humanize"):
            status = enums.BalanceTransactionStatus.humanize(status)
        return f"{amount} ({status})"

    def get_source_class(self):
        try:
            return apps.get_model("djstripe", self.type)
        except LookupError:
            raise

    def get_source_instance(self):
        return self.get_source_class().objects.get(id=self.source)

    def get_stripe_dashboard_url(self):
        return self.get_source_instance().get_stripe_dashboard_url()


class Charge(StripeModel):
    """
    To charge a credit or a debit card, you create a charge object. You can
    retrieve and refund individual charges as well as list all charges. Charges
    are identified by a unique random ID.

    Stripe documentation: https://stripe.com/docs/api?lang=python#charges
    """

    stripe_class = stripe.Charge
    expand_fields = ["balance_transaction"]
    stripe_dashboard_item_name = "payments"

    # Critical fields to keep
    amount = StripeDecimalCurrencyAmountField(help_text="Amount charged (as decimal).")
    currency = StripeCurrencyCodeField(
        help_text="The currency in which the charge was made."
    )
    balance_transaction = StripeForeignKey(
        "BalanceTransaction",
        on_delete=models.SET_NULL,
        null=True,
        help_text=(
            "The balance transaction that describes the impact of this charge "
            "on your account balance (not including refunds or disputes)."
        ),
    )
    customer = StripeForeignKey(
        "Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="charges",
        help_text="The customer associated with this charge.",
    )
    invoice = StripeForeignKey(
        "Invoice",
        on_delete=models.CASCADE,
        null=True,
        related_name="charges",
        help_text="The invoice this charge is for if one exists.",
    )
    payment_intent = StripeForeignKey(
        "PaymentIntent",
        null=True,
        on_delete=models.SET_NULL,
        related_name="charges",
        help_text="PaymentIntent associated with this charge, if one exists.",
    )
    payment_method = StripeForeignKey(
        "PaymentMethod",
        null=True,
        on_delete=models.SET_NULL,
        related_name="charges",
        help_text="PaymentMethod used in this charge.",
    )
    source = PaymentMethodForeignKey(
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="charges",
        help_text="The source used for this charge.",
    )
    status = StripeEnumField(
        enum=enums.ChargeStatus, help_text="The status of the payment."
    )

    objects = ChargeManager()

    # Property accessors for commonly used fields
    @property
    def amount_captured(self):
        return self.stripe_data.get("amount_captured")

    @property
    def amount_refunded(self):
        return self.stripe_data.get("amount_refunded")

    @property
    def application(self):
        return self.stripe_data.get("application")

    @property
    def application_fee(self):
        return self.stripe_data.get("application_fee")

    @property
    def application_fee_amount(self):
        return self.stripe_data.get("application_fee_amount")

    @property
    def billing_details(self):
        return self.stripe_data.get("billing_details")

    @property
    def captured(self):
        return self.stripe_data.get("captured")

    @property
    def dispute(self):
        return self.stripe_data.get("dispute")

    @property
    def disputed(self):
        return self.stripe_data.get("disputed")

    @property
    def on_behalf_of(self):
        return self.stripe_data.get("on_behalf_of")

    @property
    def outcome(self):
        return self.stripe_data.get("outcome")

    @property
    def paid(self):
        return self.stripe_data.get("paid")

    @property
    def payment_method_details(self):
        return self.stripe_data.get("payment_method_details")

    @property
    def receipt_email(self):
        return self.stripe_data.get("receipt_email")

    @property
    def receipt_number(self):
        return self.stripe_data.get("receipt_number")

    @property
    def receipt_url(self):
        return self.stripe_data.get("receipt_url")

    @property
    def refunded(self):
        return self.stripe_data.get("refunded")

    @property
    def shipping(self):
        return self.stripe_data.get("shipping")

    @property
    def statement_descriptor(self):
        return self.stripe_data.get("statement_descriptor")

    @property
    def statement_descriptor_suffix(self):
        return self.stripe_data.get("statement_descriptor_suffix")

    @property
    def transfer(self):
        return self.stripe_data.get("transfer")

    @property
    def transfer_data(self):
        return self.stripe_data.get("transfer_data")

    @property
    def transfer_group(self):
        return self.stripe_data.get("transfer_group")

    def __str__(self):
        amount = get_friendly_currency_amount(self.amount, self.currency)
        return f"{amount} ({self.human_readable_status})"

    @property
    def fee(self):
        if self.balance_transaction:
            return self.balance_transaction.fee

    @property
    def human_readable_status(self) -> str:
        if not self.captured:
            return "Uncaptured"
        elif self.disputed:
            return "Disputed"
        elif self.refunded:
            return "Refunded"
        return enums.ChargeStatus.humanize(self.status)

    @property
    def fraudulent(self) -> bool:
        fraud_details = self.stripe_data.get("fraud_details")
        return (
            (fraud_details and list(fraud_details.values())[0] == "fraudulent")
            if fraud_details
            else False
        )

    def _calculate_refund_amount(self, amount: Optional[Decimal]) -> int:
        """
        Returns the amount that can be refunded (in cents)
        """
        eligible_to_refund = self.amount - (self.amount_refunded or 0)
        amount_to_refund = (
            min(eligible_to_refund, amount) if amount else eligible_to_refund
        )

        return int(amount_to_refund * 100)

    def refund(
        self,
        amount: Decimal | None = None,
        reason: str | None = None,
        api_key: str | None = None,
        stripe_account: str | None = None,
    ) -> "Refund":
        """
        Initiate a refund. Returns the refund object.

        :param amount: A positive decimal amount representing how much of this charge
            to refund. If amount is not provided, then this will be a full refund.
            Can only refund up to the unrefunded amount remaining of the charge.
        :param reason: String indicating the reason for the refund.
            If set, possible values are ``duplicate``, ``fraudulent``,
            and ``requested_by_customer``. Specifying ``fraudulent`` as the reason
            when you believe the charge to be fraudulent will
            help Stripe improve their fraud detection algorithms.
        """
        api_key = api_key or self.default_api_key

        # Prefer passed in stripe_account if set.
        if not stripe_account:
            stripe_account = self._get_stripe_account_id(api_key)

        refund_obj = Refund._api_create(
            charge=self.id,
            amount=self._calculate_refund_amount(amount=amount),
            reason=reason,
            api_key=api_key,
            stripe_account=stripe_account,
        )

        return Refund.sync_from_stripe_data(
            refund_obj,
            api_key=api_key,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
        )

    def capture(self, **kwargs) -> "Charge":
        """
        Capture the payment of an existing, uncaptured, charge.
        This is the second half of the two-step payment flow, where first you
        created a charge with the capture option set to False.

        See https://stripe.com/docs/api#capture_charge
        """

        captured_charge = self.api_retrieve().capture(**kwargs)
        return self.__class__.sync_from_stripe_data(
            captured_charge, api_key=self.default_api_key
        )

    def _attach_objects_post_save_hook(
        self,
        cls,
        data,
        pending_relations=None,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
    ):
        super()._attach_objects_post_save_hook(
            cls, data, pending_relations=pending_relations, api_key=api_key
        )

        cls._stripe_object_to_refunds(
            target_cls=Refund, data=data, charge=self, api_key=api_key
        )


# TODO Add Tests
class Mandate(StripeModel):
    """
    A Mandate is a record of the permission a customer has given you to debit their payment method.

    https://stripe.com/docs/api/mandates
    """

    stripe_class = stripe.Mandate

    # Critical fields to keep
    payment_method = StripeForeignKey("paymentmethod", on_delete=models.CASCADE)

    # Property accessors for commonly used fields
    @property
    def customer_acceptance(self):
        return self.stripe_data.get("customer_acceptance")

    @property
    def payment_method_details(self):
        return self.stripe_data.get("payment_method_details")

    @property
    def status(self):
        return self.stripe_data.get("status")

    @property
    def type(self):
        return self.stripe_data.get("type")

    @property
    def multi_use(self):
        return self.stripe_data.get("multi_use")

    @property
    def single_use(self):
        return self.stripe_data.get("single_use")


class Product(StripeModel):
    """
    Products describe the specific goods or services you offer to your customers.
    For example, you might offer a Standard and Premium version of your goods or service;
    each version would be a separate Product. They can be used in conjunction with
    Prices to configure pricing in Payment Links, Checkout, and Subscriptions.

    Stripe documentation: https://stripe.com/docs/api?lang=python#products
    """

    stripe_class = stripe.Product
    stripe_dashboard_item_name = "products"

    # Critical fields to keep
    name = models.TextField(
        max_length=5000,
        help_text=(
            "The product's name, meant to be displayable to the customer. "
            "Applicable to both `service` and `good` types."
        ),
    )
    active = models.BooleanField(
        null=True,
        help_text=(
            "Whether the product is currently available for purchase. "
            "Only applicable to products of `type=good`."
        ),
    )

    # Property accessors for commonly used fields
    @property
    def url(self):
        return self.stripe_data.get("url")

    @property
    def unit_label(self):
        return self.stripe_data.get("unit_label")

    def __str__(self):
        return self.name

    @property
    def default_price(self) -> Union["Price", None]:
        default_price_id = self.stripe_data.get("default_price", None)
        if not default_price_id:
            return None
        if isinstance(default_price_id, dict):
            default_price_id = default_price_id["id"]
        return Price.objects.get(id=default_price_id)

    @property
    def type(self):
        return self.stripe_data.get("type")


class Customer(StripeModel):
    """
    Customer objects allow you to perform recurring charges and track multiple
    charges that are associated with the same customer.

    Stripe documentation: https://stripe.com/docs/api?lang=python#customers
    """

    stripe_class = stripe.Customer
    expand_fields = ["default_source", "sources"]
    stripe_dashboard_item_name = "customers"

    # Critical fields to keep

    email = models.TextField(max_length=5000, default="", blank=True)
    # default_payment_method is actually nested inside invoice_settings
    # this field is a convenience to provide the foreign key
    default_payment_method = StripeForeignKey(
        "PaymentMethod",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=(
            "default payment method used for subscriptions and invoices "
            "for the customer."
        ),
    )

    # Property accessors for commonly used fields
    @property
    def currency(self):
        return self.stripe_data.get("currency")

    @property
    def default_source(self):
        return self.stripe_data.get("default_source")

    @property
    def deleted(self):
        return self.stripe_data.get("deleted", False)

    @property
    def coupon(self):
        return self.stripe_data.get("coupon")

    @property
    def name(self):
        return self.stripe_data.get("name")

    @property
    def entitlements(self):
        return self.stripe_data.get("entitlements", [])

    # dj-stripe fields
    subscriber = models.ForeignKey(
        djstripe_settings.get_subscriber_model_string(),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="djstripe_customers",
    )
    date_purged = models.DateTimeField(null=True, editable=False)

    def __str__(self):
        if self.subscriber:
            return str(self.subscriber)

        return self.stripe_data.get("name") or self.description or self.id

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        # stripe adds a deleted attribute if the Customer has been deleted upstream
        if data.get("deleted"):
            logger.warning(
                f"This customer ({data.get('id')}) has been deleted upstream, in Stripe"
            )

        else:
            # set "deleted" key to False (default)
            data["deleted"] = False

        # Populate the object id for our default_payment_method field (or set it None)
        data["default_payment_method"] = data.get("invoice_settings", {}).get(
            "default_payment_method"
        )

        return data

    @classmethod
    def get_or_create(
        cls,
        subscriber,
        livemode=djstripe_settings.STRIPE_LIVE_MODE,
        stripe_account=None,
        api_key=None,
    ):
        """
        Get or create a dj-stripe customer.

        :param subscriber: The subscriber model instance for which to get or
            create a customer.
        :type subscriber: User

        :param livemode: Whether to get the subscriber in live or test mode.
        :type livemode: bool
        """
        api_key = api_key or djstripe_settings.get_default_api_key(livemode=livemode)

        try:
            return cls.objects.get(subscriber=subscriber, livemode=livemode), False
        except cls.DoesNotExist:
            action = f"create:{subscriber.pk}"
            idempotency_key = djstripe_settings.get_idempotency_key(
                "customer", action, livemode=livemode
            )
            return (
                cls.create(
                    subscriber,
                    idempotency_key=idempotency_key,
                    stripe_account=stripe_account,
                    livemode=livemode,
                    api_key=api_key,
                ),
                True,
            )

    @classmethod
    def create(
        cls,
        subscriber,
        idempotency_key=None,
        stripe_account=None,
        livemode: bool | None = djstripe_settings.STRIPE_LIVE_MODE,
        api_key=None,
    ):
        api_key = api_key or djstripe_settings.get_default_api_key(livemode=livemode)
        metadata = {}
        subscriber_key = djstripe_settings.SUBSCRIBER_CUSTOMER_KEY
        if subscriber_key not in ("", None):
            metadata[subscriber_key] = subscriber.pk

        try:
            # if subscriber table has a get_full_name() method, use it as name
            # ref django.contrib.auth.models.User.get_full_name
            name = subscriber.get_full_name()
        except AttributeError:
            name = None

        stripe_customer = cls._api_create(
            email=subscriber.email,
            name=name,
            idempotency_key=idempotency_key,
            metadata=metadata,
            stripe_account=stripe_account,
            livemode=livemode,
            api_key=api_key,
        )
        customer, created = cls.objects.get_or_create(
            id=stripe_customer["id"],
            defaults={
                "subscriber": subscriber,
                "livemode": stripe_customer["livemode"],
            },
        )

        return customer

    @property
    def address(self):
        return self.stripe_data.get("address")

    @property
    def balance(self) -> int:
        balance = self.stripe_data.get("balance", 0)
        return balance if balance is not None else 0

    @property
    def credits(self):
        """
        The customer is considered to have credits if their balance is below 0.
        """
        balance = self.balance or 0
        return abs(min(balance, 0))

    @property
    def delinquent(self) -> bool:
        return self.stripe_data.get("delinquent", False) or False

    @property
    def customer_payment_methods(self):
        """
        An iterable of all of the customer's payment methods
        (sources, then legacy cards)
        """
        yield from self.sources.iterator()

    @property
    def discount(self):
        return self.stripe_data.get("discount")

    @property
    def invoice_prefix(self) -> str | None:
        return self.stripe_data.get("invoice_prefix")

    @property
    def pending_charges(self):
        """
        The customer is considered to have pending charges if their balance is above 0.
        """
        return max(self.balance, 0)

    @property
    def phone(self):
        return self.stripe_data.get("phone")

    @property
    def shipping(self):
        return self.stripe_data.get("shipping")

    @property
    def preferred_locales(self):
        return self.stripe_data.get("preferred_locales")

    @property
    def tax_exempt(self):
        return self.stripe_data.get("tax_exempt")

    def subscribe(self, *, items=None, price=None, **kwargs):
        """
        Subscribes this customer to all the prices or plans in the items dict (Recommended).

        :param items: A list of up to 20 subscription items, each with an attached price
        :type list:
            :param items: A dictionary of Plan (or Plan ID) or Price (or Price ID)
            :type dict:  The price or plan to which to subscribe the customer.

        :param price: The price to which to subscribe the customer.
        :type price: Price or string (price ID)

        :param plan: The plan to which to subscribe the customer.
        :type plan: Plan or string (plan ID)
        """
        from .billing import Subscription

        if items and price:
            raise TypeError("Please define only one of items and price arguments.")

        if items is None:
            _items = [{"price": price}]
        else:
            _items = []
            for item in items:
                price = item.get("price", "")
                if "price" in item:
                    _items.append({"price": price})

        stripe_subscription = Subscription._api_create(
            items=_items, customer=self.id, **kwargs
        )

        api_key = kwargs.get("api_key") or self.default_api_key
        return Subscription.sync_from_stripe_data(stripe_subscription, api_key=api_key)

    def charge(
        self,
        amount: Decimal,
        *,
        application_fee: Decimal = None,
        source: Union[str, StripeModel] = None,
        **kwargs,
    ) -> Charge:
        """
        Creates a charge for this customer.

        :param amount: The amount to charge.
        :type amount: Decimal. Precision is 2; anything more will be ignored.
        :param source: The source to use for this charge.
            Must be a source attributed to this customer. If None, the customer's
            default source is used. Can be either the id of the source or
            the source object itself.
        :type source: string, Source
        """

        if not isinstance(amount, Decimal):
            raise ValueError("You must supply a decimal value representing dollars.")

        # Convert Source to id
        if source and isinstance(source, StripeModel):
            source = source.id

        stripe_charge = Charge._api_create(
            customer=self.id,
            amount=int(amount * 100),  # Convert dollars into cents
            application_fee=(
                int(application_fee * 100) if application_fee else None
            ),  # Convert dollars into cents
            source=source,
            **kwargs,
        )

        api_key = kwargs.get("api_key") or self.default_api_key
        return Charge.sync_from_stripe_data(stripe_charge, api_key=api_key)

    def add_invoice_item(
        self,
        amount,
        currency,
        description=None,
        discountable=None,
        invoice=None,
        metadata=None,
        subscription=None,
    ):
        """
        Adds an arbitrary charge or credit to the customer's upcoming invoice.
        Different than creating a charge. Charges are separate bills that get
        processed immediately. Invoice items are appended to the customer's next
        invoice. This is extremely useful when adding surcharges to subscriptions.

        :param amount: The amount to charge.
        :type amount: Decimal. Precision is 2; anything more will be ignored.
        :param currency: 3-letter ISO code for currency
        :type currency: string
        :param description: An arbitrary string.
        :type description: string
        :param discountable: Controls whether discounts apply to this invoice item.
            Defaults to False for prorations or negative invoice items,
            and True for all other invoice items.
        :type discountable: boolean
        :param invoice: An existing invoice to add this invoice item to.
            When left blank, the invoice item will be added to the next upcoming \
             scheduled invoice. \
             Use this when adding invoice items in response to an \
             ``invoice.created`` webhook. You cannot add an invoice \
            item to an invoice that has already been paid, attempted or closed.
        :type invoice: Invoice or string (invoice ID)
        :param metadata: A set of key/value pairs useful for storing
            additional information.
        :type metadata: dict
        :param subscription: A subscription to add this invoice item to.
            When left blank, the invoice item will be be added to the next upcoming \
            scheduled invoice. When set, scheduled invoices for subscriptions other \
            than the specified subscription will ignore the invoice item. \
            Use this when you want to express that an invoice item has been accrued \
            within the context of a particular subscription.
        :type subscription: Subscription or string (subscription ID)

        .. Notes:
        .. if you're using ``Customer.add_invoice_item()`` instead of
        .. ``Customer.add_invoice_item()``, ``invoice`` and ``subscriptions``
        .. can only be strings
        """
        from .billing import InvoiceItem

        if not isinstance(amount, Decimal):
            raise ValueError("You must supply a decimal value representing dollars.")

        # Convert Invoice to id
        if invoice is not None and isinstance(invoice, StripeModel):
            invoice = invoice.id

        # Convert Subscription to id
        if subscription is not None and isinstance(subscription, StripeModel):
            subscription = subscription.id

        stripe_invoiceitem = InvoiceItem._api_create(
            amount=int(amount * 100),  # Convert dollars into cents
            currency=currency,
            customer=self.id,
            description=description,
            discountable=discountable,
            invoice=invoice,
            metadata=metadata,
            subscription=subscription,
        )

        return InvoiceItem.sync_from_stripe_data(
            stripe_invoiceitem, api_key=self.default_api_key
        )

    def add_payment_method(self, payment_method, set_default=True):
        """
        Adds an already existing payment method to this customer's account

        :param payment_method: PaymentMethod to be attached to the customer
        :type payment_method: str, PaymentMethod
        :param set_default: If true, this will be set as the default_payment_method
        :type set_default: bool
        :rtype: PaymentMethod
        """
        from .payment_methods import PaymentMethod

        stripe_customer = self.api_retrieve()
        payment_method = PaymentMethod.attach(payment_method, stripe_customer)

        if set_default:
            stripe_customer["invoice_settings"]["default_payment_method"] = (
                payment_method.id
            )
            stripe_customer.save()

            # Refresh self from the stripe customer, this should have two effects:
            # 1) sets self.default_payment_method (we rely on logic in
            # Customer._manipulate_stripe_object_hook to do this)
            # 2) updates self.invoice_settings.default_payment_methods
            self.sync_from_stripe_data(stripe_customer, api_key=self.default_api_key)
            self.refresh_from_db()

        return payment_method

    def purge(self):
        """Customers are soft deleted as deleted customers are still accessible by the
        Stripe API and sync for all RelatedModels would fail"""
        try:
            self._api_delete()
        except InvalidRequestError as exc:
            if "No such customer:" in str(exc):
                # The exception was thrown because the stripe customer was already
                # deleted on the stripe side, ignore the exception
                pass
            else:
                # The exception was raised for another reason, re-raise it
                raise

        # toggle the deleted flag on Customer to indicate it has been
        # deleted upstream in Stripe
        self.deleted = True

        if self.subscriber:
            # Delete the idempotency key used by Customer.create()
            # So re-creating a customer for this subscriber before the key expires
            # doesn't return the older Customer data
            idempotency_key_action = f"customer:create:{self.subscriber.pk}"
            IdempotencyKey.objects.filter(action=idempotency_key_action).delete()

        self.subscriber = None

        # Remove sources
        self.default_source = None
        for source in self.sources.all():
            source.detach()

        self.date_purged = timezone.now()
        self.save()

    def _get_valid_subscriptions(self):
        """Get a list of this customer's valid subscriptions."""

        return [
            subscription
            for subscription in self.subscriptions.all()
            if subscription.is_valid()
        ]

    def is_subscribed_to(self, product: Union[Product, str]) -> bool:
        """
        Checks to see if this customer has an active subscription to the given product.

        :param product: The product for which to check for an active subscription.
        :type product: Product or string (product ID)

        :returns: True if there exists an active subscription, False otherwise.
        """

        if isinstance(product, StripeModel):
            product = product.id

        for subscription in self._get_valid_subscriptions():
            for item in subscription.items.all():
                if item.price and item.price.product.id == product:
                    return True
        return False

    def has_any_active_subscription(self):
        """
        Checks to see if this customer has an active subscription to any plan.

        :returns: True if there exists an active subscription, False otherwise.
        """

        return len(self._get_valid_subscriptions()) != 0

    @property
    def active_subscriptions(self):
        """
        Returns active subscriptions
        (subscriptions with an active status that end in the future).
        """
        return self.subscriptions.filter(
            status=enums.SubscriptionStatus.active,
            current_period_end__gt=timezone.now(),
        )

    @property
    def valid_subscriptions(self):
        """
        Returns this customer's valid subscriptions
        (subscriptions that aren't canceled or incomplete_expired).
        """
        return self.subscriptions.exclude(
            status__in=[
                enums.SubscriptionStatus.canceled,
                enums.SubscriptionStatus.incomplete_expired,
            ]
        )

    @property
    def subscription(self):
        """
        Shortcut to get this customer's subscription.

        :returns: None if the customer has no subscriptions, the subscription if
            the customer has a subscription.
        :raises MultipleSubscriptionException: Raised if the customer has multiple
            subscriptions.
            In this case, use ``Customer.subscriptions`` instead.
        """

        subscriptions = self.valid_subscriptions

        if subscriptions.count() > 1:
            raise MultipleSubscriptionException(
                "This customer has multiple subscriptions. Use Customer.subscriptions "
                "to access them."
            )
        else:
            return subscriptions.first()

    def send_invoice(self, **kwargs):
        """
        Pay and send the customer's latest invoice.

        :returns: True if an invoice was able to be created and paid, False otherwise
            (typically if there was nothing to invoice).
        """
        from .billing import Invoice

        try:
            invoice = Invoice._api_create(customer=self.id)
            invoice.pay(**kwargs)
            return True
        except InvalidRequestError:  # TODO: Check this for a more
            #                           specific error message.
            return False  # There was nothing to invoice

    def retry_unpaid_invoices(self, **kwargs):
        """Attempt to retry collecting payment on the customer's unpaid invoices."""

        self._sync_invoices()
        for invoice in self.invoices.filter(auto_advance=True).exclude(status="paid"):
            try:
                invoice.retry(**kwargs)  # Always retry unpaid invoices
            except InvalidRequestError as exc:
                if str(exc) != "Invoice is already paid":
                    raise

    def add_coupon(self, coupon, idempotency_key=None):
        """
        Add a coupon to a Customer.

        The coupon can be a Coupon object, or a valid Stripe Coupon ID.
        """
        if isinstance(coupon, StripeModel):
            coupon = coupon.id

        stripe_customer = self.api_retrieve()
        stripe_customer["coupon"] = coupon
        stripe_customer.save(idempotency_key=idempotency_key)
        return self.__class__.sync_from_stripe_data(
            stripe_customer, api_key=self.default_api_key
        )

    def upcoming_invoice(self, **kwargs):
        """Gets the upcoming preview invoice (singular) for this customer.

        See `Invoice.upcoming() <#djstripe.Invoice.upcoming>`__.

        The ``customer`` argument to the ``upcoming()`` call is automatically set
         by this method.
        """
        from .billing import Invoice

        kwargs["customer"] = self
        return Invoice.upcoming(**kwargs)

    def _attach_objects_post_save_hook(
        self,
        cls,
        data,
        pending_relations=None,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
    ):
        from .billing import Coupon
        from .payment_methods import DjstripePaymentMethod

        super()._attach_objects_post_save_hook(
            cls, data, pending_relations=pending_relations, api_key=api_key
        )

        save = False

        customer_sources = data.get("sources")
        sources = {}
        if customer_sources:
            # Have to create sources before we handle the default_source
            # We save all of them in the `sources` dict, so that we can find them
            # by id when we look at the default_source (we need the source type).
            for source in customer_sources["data"]:
                obj, _ = DjstripePaymentMethod._get_or_create_source(
                    source, source["object"], api_key=api_key
                )
                sources[source["id"]] = obj

        discount = data.get("discount")
        if discount:
            coupon, _created = Coupon._get_or_create_from_stripe_object(
                discount, "coupon", api_key=api_key
            )
            # Coupon is now accessed via stripe_data, so we don't need to save it
            pass

        if save:
            self.save()

    def _attach_objects_hook(
        self, cls, data, current_ids=None, api_key=djstripe_settings.STRIPE_SECRET_KEY
    ):
        # When we save a customer to Stripe, we add a reference to its Django PK
        # in the `django_account` key. If we find that, we re-attach that PK.
        subscriber_key = djstripe_settings.SUBSCRIBER_CUSTOMER_KEY
        if subscriber_key in ("", None):
            # Disabled. Nothing else to do.
            return

        subscriber_id = data.get("metadata", {}).get(subscriber_key)
        if subscriber_id:
            cls = djstripe_settings.get_subscriber_model()
            try:
                # We have to perform a get(), instead of just attaching the PK
                # blindly as the object may have been deleted or not exist.
                # Attempting to save that would cause an IntegrityError.
                self.subscriber = cls.objects.get(pk=subscriber_id)
            except (cls.DoesNotExist, ValueError):
                logger.warning(
                    "Could not find subscriber %r matching customer %r",
                    subscriber_id,
                    self.id,
                )
                self.subscriber = None

    # SYNC methods should be dropped in favor of the master sync infrastructure proposed
    def _sync_invoices(self, **kwargs):
        from .billing import Invoice

        api_key = kwargs.get("api_key") or self.default_api_key
        for stripe_invoice in Invoice.api_list(customer=self.id, **kwargs):
            Invoice.sync_from_stripe_data(stripe_invoice, api_key=api_key)

    def _sync_charges(self, **kwargs):
        api_key = kwargs.get("api_key") or self.default_api_key
        for stripe_charge in Charge.api_list(customer=self.id, **kwargs):
            Charge.sync_from_stripe_data(stripe_charge, api_key=api_key)

    def _sync_cards(self, **kwargs):
        from .payment_methods import Card

        api_key = kwargs.get("api_key") or self.default_api_key
        for stripe_card in Card.api_list(customer=self, **kwargs):
            Card.sync_from_stripe_data(stripe_card, api_key=api_key)

    def _sync_subscriptions(self, **kwargs):
        from .billing import Subscription

        api_key = kwargs.get("api_key") or self.default_api_key
        for stripe_subscription in Subscription.api_list(
            customer=self.id, status="all", **kwargs
        ):
            Subscription.sync_from_stripe_data(stripe_subscription, api_key=api_key)


class Dispute(StripeModel):
    """
    A dispute occurs when a customer questions your charge with their
    card issuer. When this happens, you're given the opportunity to
    respond to the dispute with evidence that shows that the charge is legitimate

    Stripe documentation: https://stripe.com/docs/api?lang=python#disputes
    """

    stripe_class = stripe.Dispute
    stripe_dashboard_item_name = "payments"

    balance_transaction = StripeForeignKey(
        "BalanceTransaction",
        null=True,
        on_delete=models.CASCADE,
        related_name="disputes",
        help_text=(
            "Balance transaction that describes the impact on your account balance."
        ),
    )
    # charge is nullable to avoid infinite sync as Charge model has a dispute field as well
    charge = StripeForeignKey(
        "Charge",
        null=True,
        on_delete=models.CASCADE,
        related_name="disputes",
        help_text="The charge that was disputed",
    )
    payment_intent = StripeForeignKey(
        "PaymentIntent",
        null=True,
        on_delete=models.CASCADE,
        related_name="disputes",
        help_text="The PaymentIntent that was disputed",
    )

    def __str__(self):
        amount = get_friendly_currency_amount(self.amount / 100, self.currency)
        status = enums.DisputeStatus.humanize(self.status)
        return f"{amount} ({status}) "

    @property
    def amount(self) -> int:
        return self.stripe_data["amount"]

    @property
    def balance_transactions(self):
        return self.stripe_data.get("balance_transactions")

    @property
    def currency(self):
        return self.stripe_data.get("currency")

    @property
    def evidence(self):
        return self.stripe_data.get("evidence")

    @property
    def evidence_details(self):
        return self.stripe_data.get("evidence_details")

    @property
    def is_charge_refundable(self):
        return self.stripe_data.get("is_charge_refundable")

    @property
    def reason(self):
        return self.stripe_data.get("reason")

    @property
    def status(self):
        return self.stripe_data.get("status")

    def get_stripe_dashboard_url(self) -> str:
        """Get the stripe dashboard url for this object."""
        return (
            f"{self._get_base_stripe_dashboard_url()}"
            f"{self.stripe_dashboard_item_name}/{self.payment_intent.id}"
        )

    def _attach_objects_post_save_hook(
        self,
        cls,
        data,
        pending_relations=None,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
    ):
        super()._attach_objects_post_save_hook(
            cls, data, pending_relations=pending_relations, api_key=api_key
        )

        # iterate and sync every balance transaction
        for stripe_balance_transaction in self.balance_transactions:
            BalanceTransaction.sync_from_stripe_data(
                stripe_balance_transaction, api_key=api_key
            )


class Event(StripeModel):
    """
    Events are Stripe's way of letting you know when something interesting
    happens in your account.
    When an interesting event occurs, a new Event object is created and POSTed
    to the configured webhook URL if the Event type matches.

    Stripe documentation: https://stripe.com/docs/api/events?lang=python
    """

    stripe_class = stripe.Event
    stripe_dashboard_item_name = "events"

    api_version = models.CharField(
        max_length=64,
        blank=True,
        help_text=(
            "the API version at which the event data was "
            "rendered. Blank for old entries only, all new entries will have this value"
        ),
    )
    data = JSONField(
        help_text=(
            "data received at webhook. data should be considered to be garbage "
            "until validity check is run and valid flag is set"
        )
    )
    request_id = models.CharField(
        max_length=50,
        help_text=(
            "Information about the request that triggered this event, "
            "for traceability purposes. If empty string then this is an old entry "
            "without that data. If Null then this is not an old entry, but a Stripe "
            "'automated' event with no associated request."
        ),
        default="",
        blank=True,
    )
    idempotency_key = models.TextField(default="", blank=True)
    type = models.CharField(max_length=250, help_text="Stripe's event description code")

    def __str__(self):
        return f"type={self.type}, id={self.id}"

    def _attach_objects_hook(
        self, cls, data, current_ids=None, api_key=djstripe_settings.STRIPE_SECRET_KEY
    ):
        if self.api_version is None:
            # as of api version 2017-02-14, the account.application.deauthorized
            # event sends None as api_version.
            # If we receive that, store an empty string instead.
            # Remove this hack if this gets fixed upstream.
            self.api_version = ""

        request_obj = data.get("request", None)
        if isinstance(request_obj, dict):
            # Format as of 2017-05-25
            self.request_id = request_obj.get("id") or ""
            self.idempotency_key = request_obj.get("idempotency_key") or ""
        else:
            # Format before 2017-05-25
            self.request_id = request_obj or ""

    @classmethod
    def process(cls, data, api_key=djstripe_settings.STRIPE_SECRET_KEY):
        qs = cls.objects.filter(id=data["id"])
        if qs.exists():
            return qs.first()

        # Rollback any DB operations in the case of failure so
        # we will retry creating and processing the event the
        # next time the webhook fires.
        with transaction.atomic():
            # process the event and create an Event Object
            ret = cls._create_from_stripe_object(data, api_key=api_key)
            ret.invoke_webhook_handlers()
            return ret

    def invoke_webhook_handlers(self):
        """
        Invokes any webhook handlers that have been registered for this event
        based on event type or event sub-type.

        See event handlers registered in the ``djstripe.event_handlers`` module
        (or handlers registered in djstripe plugins or contrib packages).
        """
        signal = WEBHOOK_SIGNALS.get(self.type)

        if signal:
            return signal.send(sender=Event, event=self)

    @cached_property
    def parts(self):
        """Gets the event category/verb as a list of parts."""
        return str(self.type).split(".")

    @cached_property
    def category(self):
        """Gets the event category string (e.g. 'customer')."""
        return self.parts[0]

    @cached_property
    def verb(self):
        """Gets the event past-tense verb string (e.g. 'updated')."""
        return ".".join(self.parts[1:])

    @property
    def customer(self):
        data = self.data["object"]
        if data["object"] == "customer":
            customer_id = get_id_from_stripe_data(data.get("id"))
        else:
            customer_id = get_id_from_stripe_data(data.get("customer"))

        if customer_id:
            return Customer._get_or_retrieve(
                id=customer_id,
                stripe_account=getattr(self.djstripe_owner_account, "id", None),
                api_key=self.default_api_key,
            )


class File(StripeModel):
    """
    This is an object representing a file hosted on Stripe's servers.
    The file may have been uploaded by yourself using the create file request
    (for example, when uploading dispute evidence) or it may have been created by
    Stripe (for example, the results of a Sigma scheduled query).

    Stripe documentation: https://stripe.com/docs/api/files?lang=python
    """

    stripe_class = stripe.File

    @classmethod
    def is_valid_object(cls, data):
        return data and data.get("object") in ("file", "file_upload")

    def __str__(self):
        return self.filename

    @property
    def filename(self):
        return self.stripe_data.get("filename")

    @property
    def purpose(self):
        return self.stripe_data.get("purpose")

    @property
    def size(self):
        return self.stripe_data.get("size")

    @property
    def type(self):
        return self.stripe_data.get("type")

    @property
    def url(self):
        return self.stripe_data.get("url")


# Alias for compatibility
# Stripe's SDK has the same alias.
# Do not remove/deprecate as long as it's present there.
FileUpload = File


class FileLink(StripeModel):
    """
    To share the contents of a File object with non-Stripe users,
    you can create a FileLink. FileLinks contain a URL that can be used
    to retrieve the contents of the file without authentication.

    Stripe documentation: https://stripe.com/docs/api/file_links?lang=python
    """

    stripe_class = stripe.FileLink

    file = StripeForeignKey("File", on_delete=models.CASCADE)

    def __str__(self):
        return self.url

    @property
    def expires_at(self):
        return self.stripe_data.get("expires_at")

    @property
    def url(self):
        return self.stripe_data.get("url")


class PaymentIntent(StripeModel):
    """
    A PaymentIntent guides you through the process of collecting a payment
    from your customer. We recommend that you create exactly one PaymentIntent for each order
    or customer session in your system. You can reference the PaymentIntent later to
    see the history of payment attempts for a particular session.

    A PaymentIntent transitions through multiple statuses throughout its lifetime as
    it interfaces with Stripe.js to perform authentication flows and ultimately
    creates at most one successful charge.

    Stripe documentation: https://stripe.com/docs/api?lang=python#payment_intents
    """

    stripe_class = stripe.PaymentIntent
    stripe_dashboard_item_name = "payments"

    customer = StripeForeignKey(
        "Customer",
        null=True,
        on_delete=models.CASCADE,
        help_text="Customer this PaymentIntent is for if one exists.",
    )
    on_behalf_of = StripeForeignKey(
        "Account",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=(
            "The account (if any) for which the funds of the "
            "PaymentIntent are intended."
        ),
        related_name="payment_intents",
    )
    payment_method = StripeForeignKey(
        "PaymentMethod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Payment method used in this PaymentIntent.",
    )

    def update(self, api_key=None, **kwargs):
        """
        Call the stripe API's modify operation for this model

        :param api_key: The api key to use for this request.
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """
        api_key = api_key or self.default_api_key
        response = self.api_retrieve(api_key=api_key)
        return response.modify(response.stripe_id, api_key=api_key, **kwargs)

    def _api_cancel(self, api_key=None, **kwargs):
        """
        Call the stripe API's cancel operation for this model

        :param api_key: The api key to use for this request.
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """
        api_key = api_key or self.default_api_key
        return self.api_retrieve(api_key=api_key).cancel(**kwargs)

    def _api_confirm(self, api_key=None, **kwargs):
        """
        Call the stripe API's confirm operation for this model.

        Confirm that your customer intends to pay with current or
        provided payment method. Upon confirmation, the PaymentIntent
        will attempt to initiate a payment.

        :param api_key: The api key to use for this request.
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """
        api_key = api_key or self.default_api_key
        return self.api_retrieve(api_key=api_key).confirm(**kwargs)


class SetupIntent(StripeModel):
    """
    A SetupIntent guides you through the process of setting up a customer's
    payment credentials for future payments. For example, you could use a SetupIntent
    to set up your customer's card without immediately collecting a payment.
    Later, you can use PaymentIntents to drive the payment flow.

    NOTE: You should not maintain long-lived, unconfirmed SetupIntents.
    For security purposes, SetupIntents older than 24 hours may no longer be valid.

    Stripe documentation: https://stripe.com/docs/api?lang=python#setup_intents
    """

    stripe_class = stripe.SetupIntent

    customer = StripeForeignKey(
        "Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Customer this SetupIntent belongs to, if one exists.",
    )
    on_behalf_of = StripeForeignKey(
        "Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The account (if any) for which the setup is intended.",
        related_name="setup_intents",
    )
    payment_method = StripeForeignKey(
        "PaymentMethod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Payment method used in this PaymentIntent.",
    )


class Payout(StripeModel):
    """
    A Payout object is created when you receive funds from Stripe, or when you initiate
    a payout to either a bank account or debit card of a connected Stripe account.

    Stripe documentation: https://stripe.com/docs/api?lang=python#payouts
    """

    expand_fields = ["destination"]
    stripe_class = stripe.Payout
    stripe_dashboard_item_name = "payouts"

    balance_transaction = StripeForeignKey(
        "BalanceTransaction",
        on_delete=models.SET_NULL,
        null=True,
        help_text=(
            "Balance transaction that describes the impact on your account balance."
        ),
    )
    currency = StripeCurrencyCodeField()
    destination = StripeForeignKey(
        "BankAccount",
        on_delete=models.PROTECT,
        null=True,
        help_text="Bank account or card the payout was sent to.",
    )
    failure_balance_transaction = StripeForeignKey(
        "BalanceTransaction",
        on_delete=models.SET_NULL,
        related_name="failure_payouts",
        null=True,
        blank=True,
        help_text=(
            "If the payout failed or was canceled, this will be the balance "
            "transaction that reversed the initial balance transaction, and "
            "puts the funds from the failed payout back in your balance."
        ),
    )
    original_payout = models.OneToOneField(
        "Payout",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=(
            "If this payout reverses another, this is the ID of the original payout."
        ),
    )
    reversed_by = models.OneToOneField(
        "Payout",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=(
            "If this payout was reversed, this is the ID of the payout that reverses"
            " this payout."
        ),
        related_name="reversed_payout",
    )

    @property
    def amount(self):
        return self.stripe_data.get("amount")

    @property
    def arrival_date(self):
        return self.stripe_data.get("arrival_date")

    @property
    def automatic(self):
        return self.stripe_data.get("automatic")

    @property
    def failure_code(self):
        return self.stripe_data.get("failure_code")

    @property
    def failure_message(self):
        return self.stripe_data.get("failure_message")

    @property
    def method(self):
        return self.stripe_data.get("method")

    @property
    def source_type(self):
        return self.stripe_data.get("source_type")

    @property
    def statement_descriptor(self):
        return self.stripe_data.get("statement_descriptor")

    @property
    def status(self):
        return self.stripe_data.get("status")

    @property
    def type(self):
        return self.stripe_data.get("type")


class Price(StripeModel):
    """
    Prices define the unit cost, currency, and (optional) billing cycle for
    both recurring and one-time purchases of products.

    Price and Plan objects are the same, but use a different representation.
    Creating a recurring Price in Stripe also makes a Plan available, and vice versa.
    This is not the case for a Price with interval=one_time.

    Price objects are a more recent API representation, support more features
    and its usage is encouraged instead of Plan objects.

    Stripe documentation:
    - https://stripe.com/docs/api/prices
    - https://stripe.com/docs/billing/prices-guide
    """

    stripe_class = stripe.Price
    expand_fields = ["product", "tiers"]
    stripe_dashboard_item_name = "prices"

    active = models.BooleanField(
        help_text="Whether the price can be used for new purchases."
    )
    currency = StripeCurrencyCodeField()
    nickname = models.CharField(
        max_length=250,
        blank=True,
        help_text="A brief description of the plan, hidden from customers.",
    )
    product = StripeForeignKey(
        "Product",
        on_delete=models.CASCADE,
        related_name="prices",
        help_text="The product this price is associated with.",
    )
    lookup_key = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="A lookup key used to retrieve prices dynamically from a static string.",
    )

    @property
    def billing_scheme(self):
        return self.stripe_data.get("billing_scheme")

    @property
    def recurring(self):
        return self.stripe_data.get("recurring")

    @property
    def tiers(self):
        return self.stripe_data.get("tiers")

    @property
    def tiers_mode(self):
        return self.stripe_data.get("tiers_mode")

    @property
    def transform_quantity(self):
        return self.stripe_data.get("transform_quantity")

    @property
    def type(self):
        return self.stripe_data.get("type")

    @property
    def unit_amount(self):
        return self.stripe_data.get("unit_amount")

    @property
    def unit_amount_decimal(self):
        return self.stripe_data.get("unit_amount_decimal")

    @classmethod
    def get_or_create(cls, **kwargs):
        """Get or create a Price."""

        try:
            return cls.objects.get(id=kwargs["id"]), False
        except cls.DoesNotExist:
            return cls.create(**kwargs), True

    @classmethod
    def create(cls, **kwargs):
        # A few minor things are changed in the api-version of the create call
        api_kwargs = kwargs.copy()
        if api_kwargs["unit_amount"]:
            api_kwargs["unit_amount"] = int(api_kwargs["unit_amount"] * 100)

        if isinstance(api_kwargs.get("product"), StripeModel):
            api_kwargs["product"] = api_kwargs["product"].id

        stripe_price = cls._api_create(**api_kwargs)

        api_key = api_kwargs.get("api_key") or djstripe_settings.STRIPE_SECRET_KEY
        price = cls.sync_from_stripe_data(stripe_price, api_key=api_key)

        return price

    def __str__(self):
        return f"{self.human_readable_price} for {self.product.name}"

    @property
    def human_readable_price(self):
        if self.billing_scheme == "per_unit":
            unit_amount = (self.unit_amount or 0) / 100
            amount = get_friendly_currency_amount(unit_amount, self.currency)
        elif self.tiers:
            # tiered billing scheme
            tier_1 = self.tiers[0]
            formatted_unit_amount_tier_1 = get_friendly_currency_amount(
                (tier_1["unit_amount"] or 0) / 100, self.currency
            )
            amount = f"Starts at {formatted_unit_amount_tier_1} per unit"

            # stripe shows flat fee even if it is set to 0.00
            flat_amount_tier_1 = tier_1["flat_amount"]
            if flat_amount_tier_1 is not None:
                formatted_flat_amount_tier_1 = get_friendly_currency_amount(
                    flat_amount_tier_1 / 100, self.currency
                )
                amount = f"{amount} + {formatted_flat_amount_tier_1}"
        else:
            amount = "0"

        format_args = {"amount": amount}

        if self.recurring:
            interval_count = self.recurring["interval_count"]
            if interval_count == 1:
                interval = {
                    "day": _("day"),
                    "week": _("week"),
                    "month": _("month"),
                    "year": _("year"),
                }[self.recurring["interval"]]
                template = _("{amount}/{interval}")
                format_args["interval"] = interval
            else:
                interval = {
                    "day": _("days"),
                    "week": _("weeks"),
                    "month": _("months"),
                    "year": _("years"),
                }[self.recurring["interval"]]
                template = _("{amount} / every {interval_count} {interval}")
                format_args["interval"] = interval
                format_args["interval_count"] = interval_count

        else:
            template = _("{amount} (one time)")

        return format_lazy(template, **format_args)


class Refund(StripeModel):
    """
    Refund objects allow you to refund a charge that has previously been created
    but not yet refunded. Funds will be refunded to the credit or debit card
    that was originally charged.

    Stripe documentation: https://stripe.com/docs/api?lang=python#refund_object
    """

    stripe_class = stripe.Refund

    amount = StripeQuantumCurrencyAmountField(help_text="Amount, in cents.")
    balance_transaction = StripeForeignKey(
        "BalanceTransaction",
        on_delete=models.SET_NULL,
        null=True,
        help_text=(
            "Balance transaction that describes the impact on your account balance."
        ),
    )
    charge = StripeForeignKey(
        "Charge",
        on_delete=models.CASCADE,
        related_name="refunds",
        help_text="The charge that was refunded",
    )
    currency = StripeCurrencyCodeField()
    failure_balance_transaction = StripeForeignKey(
        "BalanceTransaction",
        on_delete=models.SET_NULL,
        related_name="failure_refunds",
        null=True,
        blank=True,
        help_text=(
            "If the refund failed, this balance transaction describes the "
            "adjustment made on your account balance that reverses the initial "
            "balance transaction."
        ),
    )

    def get_stripe_dashboard_url(self):
        return self.charge.get_stripe_dashboard_url()

    @property
    def failure_reason(self):
        return self.stripe_data.get("failure_reason")

    @property
    def reason(self):
        return self.stripe_data.get("reason")

    @property
    def receipt_number(self):
        return self.stripe_data.get("receipt_number")

    @property
    def status(self):
        return self.stripe_data.get("status")
