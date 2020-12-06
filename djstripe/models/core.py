import warnings
from decimal import Decimal
from typing import Optional, Union

import stripe
from django.apps import apps
from django.db import models, transaction
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from stripe.error import InvalidRequestError

from .. import enums
from .. import settings as djstripe_settings
from .. import webhooks
from ..exceptions import MultipleSubscriptionException
from ..fields import (
    JSONField,
    PaymentMethodForeignKey,
    StripeCurrencyCodeField,
    StripeDateTimeField,
    StripeDecimalCurrencyAmountField,
    StripeEnumField,
    StripeForeignKey,
    StripeIdField,
    StripeQuantumCurrencyAmountField,
)
from ..managers import ChargeManager
from ..signals import WEBHOOK_SIGNALS
from ..utils import get_friendly_currency_amount
from .base import IdempotencyKey, StripeModel, logger

# Override the default API version used by the Stripe library.
djstripe_settings.set_stripe_api_version()


class BalanceTransaction(StripeModel):
    """
    A single transaction that updates the Stripe balance.

    Stripe documentation: https://stripe.com/docs/api#balance_transaction_object
    """

    stripe_class = stripe.BalanceTransaction

    amount = StripeQuantumCurrencyAmountField(
        help_text="Gross amount of the transaction, in cents."
    )
    available_on = StripeDateTimeField(
        help_text=(
            "The date the transaction's net funds "
            "will become available in the Stripe balance."
        )
    )
    currency = StripeCurrencyCodeField()
    exchange_rate = models.DecimalField(null=True, decimal_places=6, max_digits=8)
    fee = StripeQuantumCurrencyAmountField(
        help_text="Fee (in cents) paid for this transaction."
    )
    fee_details = JSONField()
    net = StripeQuantumCurrencyAmountField(
        help_text="Net amount of the transaction, in cents."
    )
    source = StripeIdField()
    reporting_category = StripeEnumField(
        enum=enums.BalanceTransactionReportingCategory,
        help_text=(
            "More information: https://stripe.com/docs/reports/reporting-categories"
        ),
    )
    status = StripeEnumField(enum=enums.BalanceTransactionStatus)
    type = StripeEnumField(enum=enums.BalanceTransactionType)

    def get_source_class(self):
        return apps.get_model("djstripe", self.type)

    def get_source_instance(self):
        return self.get_source_class().objects.get(id=self.source)

    def get_stripe_dashboard_url(self):
        return self.get_source_instance().get_stripe_dashboard_url()


class Charge(StripeModel):
    """
    To charge a credit or a debit card, you create a charge object. You can
    retrieve and refund individual charges as well as list all charges. Charges
    are identified by a unique random ID.

    Stripe documentation: https://stripe.com/docs/api/python#charges
    """

    stripe_class = stripe.Charge
    expand_fields = ["balance_transaction"]
    stripe_dashboard_item_name = "payments"

    amount = StripeDecimalCurrencyAmountField(help_text="Amount charged (as decimal).")
    amount_captured = StripeDecimalCurrencyAmountField(
        null=True,
        help_text=(
            "Amount (as decimal) captured (can be less than the amount attribute "
            "on the charge if a partial capture was issued)."
        ),
    )
    amount_refunded = StripeDecimalCurrencyAmountField(
        help_text=(
            "Amount (as decimal) refunded (can be less than the amount attribute on "
            "the charge if a partial refund was issued)."
        )
    )
    application = models.CharField(
        max_length=255,
        blank=True,
        help_text="ID of the Connect application that created the charge.",
    )
    application_fee = StripeForeignKey(
        "ApplicationFee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fee_for_charge",
        help_text="The application fee (if any) for the charge.",
    )
    application_fee_amount = StripeDecimalCurrencyAmountField(
        null=True,
        blank=True,
        help_text="The amount (as decimal) of the application fee (if any) "
        "requested for the charge.",
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
    billing_details = JSONField(
        null=True,
        help_text="Billing information associated with the PaymentMethod at the "
        "time of the transaction.",
    )
    calculated_statement_descriptor = models.CharField(
        max_length=22,
        default="",
        help_text="The full statement descriptor that is passed to card networks, "
        "and that is displayed on your customers’ credit card and bank statements. "
        "Allows you to see what the statement descriptor looks like after the "
        "static and dynamic portions are combined.",
    )
    captured = models.BooleanField(
        default=False,
        help_text="If the charge was created without capturing, this boolean "
        "represents whether or not it is still uncaptured or has since been captured.",
    )
    currency = StripeCurrencyCodeField(
        help_text="The currency in which the charge was made."
    )
    customer = StripeForeignKey(
        "Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="charges",
        help_text="The customer associated with this charge.",
    )
    dispute = StripeForeignKey(
        "Dispute",
        on_delete=models.SET_NULL,
        null=True,
        related_name="charges",
        help_text="Details about the dispute if the charge has been disputed.",
    )
    disputed = models.BooleanField(
        default=False,
        help_text="Whether the charge has been disputed.",
    )
    failure_code = StripeEnumField(
        enum=enums.ApiErrorCode,
        default="",
        blank=True,
        help_text="Error code explaining reason for charge failure if available.",
    )
    failure_message = models.TextField(
        max_length=5000,
        default="",
        blank=True,
        help_text="Message to user further explaining reason "
        "for charge failure if available.",
    )
    fraud_details = JSONField(
        help_text="Hash with information on fraud assessments for the charge.",
        null=True,
        blank=True,
    )
    invoice = StripeForeignKey(
        "Invoice",
        on_delete=models.CASCADE,
        null=True,
        related_name="charges",
        help_text="The invoice this charge is for if one exists.",
    )
    # TODO: order (requires Order model)
    on_behalf_of = StripeForeignKey(
        "Account",
        on_delete=models.CASCADE,
        null=True,
        related_name="charges",
        help_text="The account (if any) the charge was made on behalf of "
        "without triggering an automatic transfer.",
    )
    outcome = JSONField(
        help_text="Details about whether or not the payment was accepted, and why.",
        null=True,
        blank=True,
    )
    paid = models.BooleanField(
        default=False,
        help_text="True if the charge succeeded, "
        "or was successfully authorized for later capture, False otherwise.",
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
    payment_method_details = JSONField(
        help_text="Details about the payment method at the time of the transaction.",
        null=True,
        blank=True,
    )
    receipt_email = models.TextField(
        max_length=800,  # yup, 800.
        default="",
        blank=True,
        help_text="The email address that the receipt for this charge was sent to.",
    )
    receipt_number = models.CharField(
        max_length=14,
        default="",
        blank=True,
        help_text="The transaction number that appears "
        "on email receipts sent for this charge.",
    )
    receipt_url = models.TextField(
        max_length=5000,
        default="",
        blank=True,
        help_text="This is the URL to view the receipt for this charge. "
        "The receipt is kept up-to-date to the latest state of the charge, "
        "including any refunds. If the charge is for an Invoice, "
        "the receipt will be stylized as an Invoice receipt.",
    )
    refunded = models.BooleanField(
        default=False,
        help_text="Whether or not the charge has been fully refunded. "
        "If the charge is only partially refunded, "
        "this attribute will still be false.",
    )
    # TODO: review (requires Review model)
    shipping = JSONField(
        null=True, blank=True, help_text="Shipping information for the charge"
    )
    source = PaymentMethodForeignKey(
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="charges",
        help_text="The source used for this charge.",
    )
    source_transfer = StripeForeignKey(
        "Transfer",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="The transfer which created this charge. Only present if the "
        "charge came from another Stripe account.",
        related_name="+",
    )
    statement_descriptor = models.CharField(
        max_length=22,
        null=True,
        blank=True,
        help_text="For card charges, use statement_descriptor_suffix instead. "
        "Otherwise, you can use this value as the complete description of a "
        "charge on your customers’ statements. Must contain at least one letter, "
        "maximum 22 characters.",
    )
    statement_descriptor_suffix = models.CharField(
        max_length=22,
        null=True,
        blank=True,
        help_text="Provides information about the charge that customers see on "
        "their statements. Concatenated with the prefix (shortened descriptor) "
        "or statement descriptor that's set on the account to form the "
        "complete statement descriptor. "
        "Maximum 22 characters for the concatenated descriptor.",
    )
    status = StripeEnumField(
        enum=enums.ChargeStatus, help_text="The status of the payment."
    )
    transfer = StripeForeignKey(
        "Transfer",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=(
            "The transfer to the `destination` account (only applicable if "
            "the charge was created using the `destination` parameter)."
        ),
    )
    transfer_data = JSONField(
        null=True,
        blank=True,
        help_text="An optional dictionary including the account to automatically "
        "transfer to as part of a destination charge.",
    )
    transfer_group = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="A string that identifies this transaction as part of a group.",
    )

    objects = ChargeManager()

    def __str__(self):
        amount = self.human_readable_amount
        status = self.human_readable_status
        if not status:
            return amount
        return "{amount} ({status})".format(amount=amount, status=status)

    @property
    def account(self):
        warnings.warn(
            "Charge.account is deprecated and will be removed in 2.5.0. "
            "Use .on_behalf_of or .djstripe_owner_account instead.",
            DeprecationWarning,
        )
        return self.on_behalf_of

    @property
    def fee(self):
        if self.balance_transaction:
            return self.balance_transaction.fee

    @property
    def human_readable_amount(self) -> str:
        return get_friendly_currency_amount(self.amount, self.currency)

    @property
    def human_readable_status(self) -> str:
        if not self.captured:
            return "Uncaptured"
        elif self.disputed:
            return "Disputed"
        elif self.refunded:
            return "Refunded"
        elif self.amount_refunded:
            return "Partially refunded"
        elif self.status == enums.ChargeStatus.failed:
            return "Failed"

        return ""

    @property
    def fraudulent(self) -> bool:
        return (
            self.fraud_details and list(self.fraud_details.values())[0] == "fraudulent"
        )

    def _attach_objects_hook(self, cls, data, current_ids=None):
        from .payment_methods import DjstripePaymentMethod

        # Source doesn't always appear to be present, so handle the case
        # where it is missing.
        source_data = data.get("source")
        if not source_data:
            return

        source_type = source_data.get("object")
        if not source_type:
            return

        self.source, _ = DjstripePaymentMethod._get_or_create_source(
            data=source_data, source_type=source_type
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

    def refund(self, amount: Decimal = None, reason: str = None) -> "Charge":
        """
        Initiate a refund. Returns the charge object.

        :param amount: A positive decimal amount representing how much of this charge
            to refund. If amount is not provided, then this will be a full refund.
            Can only refund up to the unrefunded amount remaining of the charge.
        :param reason: String indicating the reason for the refund.
            If set, possible values are ``duplicate``, ``fraudulent``,
            and ``requested_by_customer``. Specifying ``fraudulent`` as the reason
            when you believe the charge to be fraudulent will
            help Stripe improve their fraud detection algorithms.
        """
        charge_obj = self.api_retrieve().refund(
            amount=self._calculate_refund_amount(amount=amount), reason=reason
        )
        return self.__class__.sync_from_stripe_data(charge_obj)

    def capture(self, **kwargs) -> "Charge":
        """
        Capture the payment of an existing, uncaptured, charge.
        This is the second half of the two-step payment flow, where first you
        created a charge with the capture option set to False.

        See https://stripe.com/docs/api#capture_charge
        """

        captured_charge = self.api_retrieve().capture(**kwargs)
        return self.__class__.sync_from_stripe_data(captured_charge)

    def _attach_objects_post_save_hook(self, cls, data, pending_relations=None):
        super()._attach_objects_post_save_hook(
            cls, data, pending_relations=pending_relations
        )

        cls._stripe_object_to_refunds(target_cls=Refund, data=data, charge=self)


class Product(StripeModel):
    """
    Stripe documentation:
    - https://stripe.com/docs/api#products
    - https://stripe.com/docs/api#service_products
    """

    stripe_class = stripe.Product
    stripe_dashboard_item_name = "products"

    # Fields applicable to both `good` and `service`
    name = models.TextField(
        max_length=5000,
        help_text=(
            "The product's name, meant to be displayable to the customer. "
            "Applicable to both `service` and `good` types."
        ),
    )
    type = StripeEnumField(
        enum=enums.ProductType,
        help_text=(
            "The type of the product. The product is either of type `good`, which is "
            "eligible for use with Orders and SKUs, or `service`, which is eligible "
            "for use with Subscriptions and Plans."
        ),
    )

    # Fields applicable to `good` only
    active = models.BooleanField(
        null=True,
        help_text=(
            "Whether the product is currently available for purchase. "
            "Only applicable to products of `type=good`."
        ),
    )
    attributes = JSONField(
        null=True,
        blank=True,
        help_text=(
            "A list of up to 5 attributes that each SKU can provide values for "
            '(e.g., `["color", "size"]`). Only applicable to products of `type=good`.'
        ),
    )
    caption = models.TextField(
        default="",
        blank=True,
        max_length=5000,
        help_text=(
            "A short one-line description of the product, meant to be displayable"
            "to the customer. Only applicable to products of `type=good`."
        ),
    )
    deactivate_on = JSONField(
        null=True,
        blank=True,
        help_text=(
            "An array of connect application identifiers that cannot purchase "
            "this product. Only applicable to products of `type=good`."
        ),
    )
    images = JSONField(
        null=True,
        blank=True,
        help_text=(
            "A list of up to 8 URLs of images for this product, meant to be "
            "displayable to the customer. Only applicable to products of `type=good`."
        ),
    )
    package_dimensions = JSONField(
        null=True,
        blank=True,
        help_text=(
            "The dimensions of this product for shipping purposes. "
            "A SKU associated with this product can override this value by having its "
            "own `package_dimensions`. Only applicable to products of `type=good`."
        ),
    )
    shippable = models.BooleanField(
        null=True,
        blank=True,
        help_text=(
            "Whether this product is a shipped good. "
            "Only applicable to products of `type=good`."
        ),
    )
    url = models.CharField(
        max_length=799,
        null=True,
        blank=True,
        help_text=(
            "A URL of a publicly-accessible webpage for this product. "
            "Only applicable to products of `type=good`."
        ),
    )

    # Fields available to `service` only
    statement_descriptor = models.CharField(
        max_length=22,
        default="",
        blank=True,
        help_text=(
            "Extra information about a product which will appear on your customer's "
            "credit card statement. In the case that multiple products are billed at "
            "once, the first statement descriptor will be used. "
            "Only available on products of type=`service`."
        ),
    )
    unit_label = models.CharField(max_length=12, default="", blank=True)

    def __str__(self):
        return self.name


class Customer(StripeModel):
    """
    Customer objects allow you to perform recurring charges and track multiple
    charges that are associated with the same customer.

    Stripe documentation: https://stripe.com/docs/api/python#customers
    """

    stripe_class = stripe.Customer
    expand_fields = ["default_source", "sources"]
    stripe_dashboard_item_name = "customers"

    address = JSONField(null=True, blank=True, help_text="The customer's address.")
    balance = StripeQuantumCurrencyAmountField(
        default=0,
        help_text=(
            "Current balance (in cents), if any, being stored on the customer's "
            "account. "
            "If negative, the customer has credit to apply to the next invoice. "
            "If positive, the customer has an amount owed that will be added to the "
            "next invoice. The balance does not refer to any unpaid invoices; it "
            "solely takes into account amounts that have yet to be successfully "
            "applied to any invoice. This balance is only taken into account for "
            "recurring billing purposes (i.e., subscriptions, invoices, invoice items)."
        ),
    )
    currency = StripeCurrencyCodeField(
        default="",
        help_text="The currency the customer can be charged in for "
        "recurring billing purposes",
    )
    default_source = PaymentMethodForeignKey(
        on_delete=models.SET_NULL, null=True, blank=True, related_name="customers"
    )
    delinquent = models.BooleanField(
        default=False,
        help_text="Whether or not the latest charge for the customer's "
        "latest invoice has failed.",
    )
    # <discount>
    coupon = models.ForeignKey(
        "Coupon", null=True, blank=True, on_delete=models.SET_NULL
    )
    coupon_start = StripeDateTimeField(
        null=True,
        blank=True,
        editable=False,
        help_text="If a coupon is present, the date at which it was applied.",
    )
    coupon_end = StripeDateTimeField(
        null=True,
        blank=True,
        editable=False,
        help_text="If a coupon is present and has a limited duration, "
        "the date that the discount will end.",
    )
    # </discount>
    email = models.TextField(max_length=5000, default="", blank=True)
    invoice_prefix = models.CharField(
        default="",
        blank=True,
        max_length=255,
        help_text=(
            "The prefix for the customer used to generate unique invoice numbers."
        ),
    )
    invoice_settings = JSONField(
        null=True, blank=True, help_text="The customer's default invoice settings."
    )
    # default_payment_method is actually nested inside invoice_settings
    # this field is a convenience to provide the foreign key
    default_payment_method = StripeForeignKey(
        "PaymentMethod",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="default payment method used for subscriptions and invoices "
        "for the customer.",
    )
    name = models.TextField(
        max_length=5000,
        default="",
        blank=True,
        help_text="The customer's full name or business name.",
    )
    phone = models.TextField(
        max_length=5000,
        default="",
        blank=True,
        help_text="The customer's phone number.",
    )
    preferred_locales = JSONField(
        null=True,
        blank=True,
        help_text=(
            "The customer's preferred locales (languages), ordered by preference."
        ),
    )
    shipping = JSONField(
        null=True,
        blank=True,
        help_text="Shipping information associated with the customer.",
    )
    tax_exempt = StripeEnumField(
        enum=enums.CustomerTaxExempt,
        default="",
        help_text="Describes the customer's tax exemption status. When set to reverse, "
        'invoice and receipt PDFs include the text "Reverse charge".',
    )

    # dj-stripe fields
    subscriber = models.ForeignKey(
        djstripe_settings.get_subscriber_model_string(),
        null=True,
        on_delete=models.SET_NULL,
        related_name="djstripe_customers",
    )
    date_purged = models.DateTimeField(null=True, editable=False)

    class Meta:
        unique_together = ("subscriber", "livemode", "djstripe_owner_account")

    def __str__(self):
        if self.subscriber:
            return str(self.subscriber)

        return self.name or self.description or self.id

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        discount = data.get("discount")
        if discount:
            data["coupon_start"] = discount["start"]
            data["coupon_end"] = discount["end"]

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
    ):
        """
        Get or create a dj-stripe customer.

        :param subscriber: The subscriber model instance for which to get or
            create a customer.
        :type subscriber: User

        :param livemode: Whether to get the subscriber in live or test mode.
        :type livemode: bool
        """

        try:
            return Customer.objects.get(subscriber=subscriber, livemode=livemode), False
        except Customer.DoesNotExist:
            action = "create:{}".format(subscriber.pk)
            idempotency_key = djstripe_settings.get_idempotency_key(
                "customer", action, livemode
            )
            return (
                cls.create(
                    subscriber,
                    idempotency_key=idempotency_key,
                    stripe_account=stripe_account,
                ),
                True,
            )

    @classmethod
    def create(cls, subscriber, idempotency_key=None, stripe_account=None):
        metadata = {}
        subscriber_key = djstripe_settings.SUBSCRIBER_CUSTOMER_KEY
        if subscriber_key not in ("", None):
            metadata[subscriber_key] = subscriber.pk

        stripe_customer = cls._api_create(
            email=subscriber.email,
            idempotency_key=idempotency_key,
            metadata=metadata,
            stripe_account=stripe_account,
        )
        customer, created = Customer.objects.get_or_create(
            id=stripe_customer["id"],
            defaults={
                "subscriber": subscriber,
                "livemode": stripe_customer["livemode"],
                "balance": stripe_customer.get("balance", 0),
                "delinquent": stripe_customer.get("delinquent", False),
            },
        )

        return customer

    @property
    def credits(self):
        """
        The customer is considered to have credits if their balance is below 0.
        """
        return abs(min(self.balance, 0))

    @property
    def customer_payment_methods(self):
        """
        An iterable of all of the customer's payment methods
        (sources, then legacy cards)
        """
        for source in self.sources.iterator():
            yield source

        for card in self.legacy_cards.iterator():
            yield card

    @property
    def pending_charges(self):
        """
        The customer is considered to have pending charges if their balance is above 0.
        """
        return max(self.balance, 0)

    def subscribe(self, price=None, plan=None, charge_immediately=True, **kwargs):
        """
        Subscribes this customer to a price.
        NOTE: Only one item is supported at the moment.

        :param price: The price to which to subscribe the customer.
        :type price: Price or string (price ID)
        :param plan: The plan to which to subscribe the customer.
        :type plan: Plan or string (plan ID)
        :param charge_immediately: Whether or not to charge for
            the subscription upon creation.
            If False, an invoice will be created at the end of this period.
        :type charge_immediately: boolean

        .. Notes:
        .. ``charge_immediately`` is only available on ``Customer.subscribe()``
        .. if you're using ``Customer.subscribe()``
        .. instead of ``Customer.subscribe()``, ``plan`` can only be a string
        """
        from .billing import Subscription

        if price and plan:
            raise TypeError("price and plan arguments cannot both be defined.")

        price = price or plan

        if not price:
            raise TypeError("you need to set either price or plan")

        # Convert Price to id
        if isinstance(price, StripeModel):
            price = price.id

        stripe_subscription = Subscription._api_create(
            items=[{"price": price}], customer=self.id, **kwargs
        )

        if charge_immediately:
            self.send_invoice()

        return Subscription.sync_from_stripe_data(stripe_subscription)

    def charge(
        self,
        amount: Decimal,
        *,
        application_fee: Decimal = None,
        source: Union[str, StripeModel] = None,
        **kwargs
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
            application_fee=int(application_fee * 100)
            if application_fee
            else None,  # Convert dollars into cents
            source=source,
            **kwargs
        )

        return Charge.sync_from_stripe_data(stripe_charge)

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

        return InvoiceItem.sync_from_stripe_data(stripe_invoiceitem)

    def add_card(self, source, set_default=True):
        """
        Adds a card to this customer's account.

        :param source: Either a token, like the ones returned by our Stripe.js, or a
            dictionary containing a user's credit card details.
            Stripe will automatically validate the card.
        :type source: string, dict
        :param set_default: Whether or not to set the source as the customer's
            default source
        :type set_default: boolean

        """
        from .payment_methods import DjstripePaymentMethod

        stripe_customer = self.api_retrieve()
        new_stripe_payment_method = stripe_customer.sources.create(source=source)

        if set_default:
            stripe_customer.default_source = new_stripe_payment_method["id"]
            stripe_customer.save()

        new_payment_method = DjstripePaymentMethod.from_stripe_object(
            new_stripe_payment_method
        )

        # Change the default source
        if set_default:
            self.default_source = new_payment_method
            self.save()

        return new_payment_method.resolve()

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
            stripe_customer["invoice_settings"][
                "default_payment_method"
            ] = payment_method.id
            stripe_customer.save()

            # Refresh self from the stripe customer, this should have two effects:
            # 1) sets self.default_payment_method (we rely on logic in
            # Customer._manipulate_stripe_object_hook to do this)
            # 2) updates self.invoice_settings.default_payment_methods
            self.sync_from_stripe_data(stripe_customer)
            self.refresh_from_db()

        return payment_method

    def purge(self):
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

        if self.subscriber:
            # Delete the idempotency key used by Customer.create()
            # So re-creating a customer for this subscriber before the key expires
            # doesn't return the older Customer data
            idempotency_key_action = "customer:create:{}".format(self.subscriber.pk)
            IdempotencyKey.objects.filter(action=idempotency_key_action).delete()

        self.subscriber = None

        # Remove sources
        self.default_source = None
        for source in self.legacy_cards.all():
            source.remove()

        for source in self.sources.all():
            source.detach()

        self.date_purged = timezone.now()
        self.save()

    # TODO: Override Queryset.delete() with a custom manager,
    #  since this doesn't get called in bulk deletes
    #  (or cascades, but that's another matter)
    def delete(self, using=None, keep_parents=False):
        """
        Overriding the delete method to keep the customer in the records.
        All identifying information is removed via the purge() method.

        The only way to delete a customer is to use SQL.
        """

        self.purge()

    def _get_valid_subscriptions(self):
        """ Get a list of this customer's valid subscriptions."""

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

    def has_active_subscription(self, plan=None):
        """
        Checks to see if this customer has an active subscription to the given plan.

        :param plan: The plan for which to check for an active subscription.
            If plan is None and there exists only one active subscription,
            this method will check if that subscription is valid.
            Calling this method with no plan and multiple valid subscriptions
            for this customer will throw an exception.
        :type plan: Plan or string (plan ID)

        :returns: True if there exists an active subscription, False otherwise.
        :throws: TypeError if ``plan`` is None and more than one active subscription
            exists for this customer.
        """

        warnings.warn(
            "has_active_subscription is deprecated in favor of `is_subscribed_to` "
            "and will be removed in a future release.",
            DeprecationWarning,
        )

        if plan is None:
            valid_subscriptions = self._get_valid_subscriptions()

            if len(valid_subscriptions) == 0:
                return False
            elif len(valid_subscriptions) == 1:
                return True
            else:
                raise TypeError(
                    "plan cannot be None if more than one valid subscription "
                    "exists for this customer."
                )
        else:
            # Convert Plan to id
            if isinstance(plan, StripeModel):
                plan = plan.id

            return any(
                [
                    subscription.is_valid()
                    for subscription in self.subscriptions.filter(plan__id=plan)
                ]
            )

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

    def can_charge(self):
        """Determines if this customer is able to be charged."""

        return (
            self.has_valid_source() or self.default_payment_method is not None
        ) and self.date_purged is None

    def send_invoice(self):
        """
        Pay and send the customer's latest invoice.

        :returns: True if an invoice was able to be created and paid, False otherwise
            (typically if there was nothing to invoice).
        """
        from .billing import Invoice

        try:
            invoice = Invoice._api_create(customer=self.id)
            invoice.pay()
            return True
        except InvalidRequestError:  # TODO: Check this for a more
            #                           specific error message.
            return False  # There was nothing to invoice

    def retry_unpaid_invoices(self):
        """ Attempt to retry collecting payment on the customer's unpaid invoices."""

        self._sync_invoices()
        for invoice in self.invoices.filter(auto_advance=True).exclude(status="paid"):
            try:
                invoice.retry()  # Always retry unpaid invoices
            except InvalidRequestError as exc:
                if str(exc) != "Invoice is already paid":
                    raise

    def has_valid_source(self):
        """ Check whether the customer has a valid payment source."""
        return self.default_source is not None

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
        return self.__class__.sync_from_stripe_data(stripe_customer)

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
        self, cls, data, pending_relations=None
    ):  # noqa (function complexity)
        from .billing import Coupon
        from .payment_methods import DjstripePaymentMethod

        super()._attach_objects_post_save_hook(
            cls, data, pending_relations=pending_relations
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
                    source, source["object"]
                )
                sources[source["id"]] = obj

        default_source = data.get("default_source")
        if default_source:
            if isinstance(default_source, str):
                default_source_id = default_source
            else:
                default_source_id = default_source["id"]

            if default_source_id in sources:
                source = sources[default_source_id]
                save = self.default_source != source
                self.default_source = source

        discount = data.get("discount")
        if discount:
            coupon, _created = Coupon._get_or_create_from_stripe_object(
                discount, "coupon"
            )
            if coupon and coupon != self.coupon:
                self.coupon = coupon
                save = True
        elif self.coupon:
            self.coupon = None
            save = True

        if save:
            self.save()

    def _attach_objects_hook(self, cls, data, current_ids=None):
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

        for stripe_invoice in Invoice.api_list(customer=self.id, **kwargs):
            Invoice.sync_from_stripe_data(stripe_invoice)

    def _sync_charges(self, **kwargs):
        for stripe_charge in Charge.api_list(customer=self.id, **kwargs):
            Charge.sync_from_stripe_data(stripe_charge)

    def _sync_cards(self, **kwargs):
        from .payment_methods import Card

        for stripe_card in Card.api_list(customer=self, **kwargs):
            Card.sync_from_stripe_data(stripe_card)

    def _sync_subscriptions(self, **kwargs):
        from .billing import Subscription

        for stripe_subscription in Subscription.api_list(
            customer=self.id, status="all", **kwargs
        ):
            Subscription.sync_from_stripe_data(stripe_subscription)

    @property
    def business_vat_id(self) -> str:
        warnings.warn(
            "Customer.business_vat_id is deprecated and will be removed in 2.5.0."
            "Use TaxId model instead.",
            DeprecationWarning,
        )

        return ""


class Dispute(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/api#disputes
    """

    stripe_class = stripe.Dispute
    stripe_dashboard_item_name = "disputes"

    amount = StripeQuantumCurrencyAmountField(
        help_text=(
            "Disputed amount (in cents). Usually the amount of the charge, "
            "but can differ "
            "(usually because of currency fluctuation or because only part of "
            "the order is disputed)."
        )
    )
    currency = StripeCurrencyCodeField()
    evidence = JSONField(help_text="Evidence provided to respond to a dispute.")
    evidence_details = JSONField(help_text="Information about the evidence submission.")
    is_charge_refundable = models.BooleanField(
        help_text=(
            "If true, it is still possible to refund the disputed payment. "
            "Once the payment has been fully refunded, no further funds will "
            "be withdrawn from your Stripe account as a result of this dispute."
        )
    )
    reason = StripeEnumField(enum=enums.DisputeReason)
    status = StripeEnumField(enum=enums.DisputeStatus)


class Event(StripeModel):
    """
    Events are Stripe's way of letting you know when something interesting
    happens in your account.
    When an interesting event occurs, a new Event object is created and POSTed
    to the configured webhook URL if the Event type matches.

    Stripe documentation: https://stripe.com/docs/api/events
    """

    stripe_class = stripe.Event
    stripe_dashboard_item_name = "events"

    api_version = models.CharField(
        max_length=15,
        blank=True,
        help_text="the API version at which the event data was "
        "rendered. Blank for old entries only, all new entries will have this value",
    )
    data = JSONField(
        help_text="data received at webhook. data should be considered to be garbage "
        "until validity check is run and valid flag is set"
    )
    request_id = models.CharField(
        max_length=50,
        help_text="Information about the request that triggered this event, "
        "for traceability purposes. If empty string then this is an old entry "
        "without that data. If Null then this is not an old entry, but a Stripe "
        "'automated' event with no associated request.",
        default="",
        blank=True,
    )
    idempotency_key = models.TextField(default="", blank=True)
    type = models.CharField(max_length=250, help_text="Stripe's event description code")

    def str_parts(self):
        return ["type={type}".format(type=self.type)] + super().str_parts()

    def _attach_objects_hook(self, cls, data, current_ids=None):
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
    def process(cls, data):
        qs = cls.objects.filter(id=data["id"])
        if qs.exists():
            return qs.first()

        # Rollback any DB operations in the case of failure so
        # we will retry creating and processing the event the
        # next time the webhook fires.
        with transaction.atomic():
            ret = cls._create_from_stripe_object(data)
            ret.invoke_webhook_handlers()
            return ret

    def invoke_webhook_handlers(self):
        """
        Invokes any webhook handlers that have been registered for this event
        based on event type or event sub-type.

        See event handlers registered in the ``djstripe.event_handlers`` module
        (or handlers registered in djstripe plugins or contrib packages).
        """

        webhooks.call_handlers(event=self)

        signal = WEBHOOK_SIGNALS.get(self.type)
        if signal:
            return signal.send(sender=Event, event=self)

    @cached_property
    def parts(self):
        """ Gets the event category/verb as a list of parts. """
        return str(self.type).split(".")

    @cached_property
    def category(self):
        """ Gets the event category string (e.g. 'customer'). """
        return self.parts[0]

    @cached_property
    def verb(self):
        """ Gets the event past-tense verb string (e.g. 'updated'). """
        return ".".join(self.parts[1:])

    @property
    def customer(self):
        data = self.data["object"]
        if data["object"] == "customer":
            field = "id"
        else:
            field = "customer"

        if data.get(field):
            return Customer._get_or_create_from_stripe_object(data, field)[0]


class FileUpload(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/api#file_uploads
    """

    stripe_class = stripe.FileUpload

    filename = models.CharField(
        max_length=255,
        help_text="A filename for the file, suitable for saving to a filesystem.",
    )
    purpose = StripeEnumField(
        enum=enums.FileUploadPurpose, help_text="The purpose of the uploaded file."
    )
    size = models.IntegerField(help_text="The size in bytes of the file upload object.")
    type = StripeEnumField(
        enum=enums.FileUploadType, help_text="The type of the file returned."
    )
    url = models.CharField(
        max_length=200,
        help_text="A read-only URL where the uploaded file can be accessed.",
    )

    @classmethod
    def is_valid_object(cls, data):
        return "object" in data and data["object"] in ("file", "file_upload")


# Alias for compatability
# TODO - rename the model and switch this alias the other way around
#  to match stripe python
File = FileUpload


class PaymentIntent(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/api#payment_intents
    """

    stripe_class = stripe.PaymentIntent
    stripe_dashboard_item_name = "payments"

    amount = StripeQuantumCurrencyAmountField(
        help_text="Amount (in cents) intended to be collected by this PaymentIntent."
    )
    amount_capturable = StripeQuantumCurrencyAmountField(
        help_text="Amount (in cents) that can be captured from this PaymentIntent."
    )
    amount_received = StripeQuantumCurrencyAmountField(
        help_text="Amount (in cents) that was collected by this PaymentIntent."
    )
    # application
    # application_fee_amount
    canceled_at = StripeDateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text=(
            "Populated when status is canceled, this is the time at which the "
            "PaymentIntent was canceled. Measured in seconds since the Unix epoch."
        ),
    )

    cancellation_reason = StripeEnumField(
        enum=enums.PaymentIntentCancellationReason,
        blank=True,
        help_text=(
            "Reason for cancellation of this PaymentIntent, either user-provided "
            "(duplicate, fraudulent, requested_by_customer, or abandoned) or "
            "generated by Stripe internally (failed_invoice, void_invoice, "
            "or automatic)."
        ),
    )
    capture_method = StripeEnumField(
        enum=enums.CaptureMethod,
        help_text="Capture method of this PaymentIntent, one of automatic or manual.",
    )
    client_secret = models.TextField(
        max_length=5000,
        help_text=(
            "The client secret of this PaymentIntent. "
            "Used for client-side retrieval using a publishable key."
        ),
    )
    confirmation_method = StripeEnumField(
        enum=enums.ConfirmationMethod,
        help_text=(
            "Confirmation method of this PaymentIntent, one of manual or automatic."
        ),
    )
    currency = StripeCurrencyCodeField()
    customer = StripeForeignKey(
        "Customer",
        null=True,
        on_delete=models.CASCADE,
        help_text="Customer this PaymentIntent is for if one exists.",
    )
    description = models.TextField(
        max_length=1000,
        default="",
        blank=True,
        help_text=(
            "An arbitrary string attached to the object. "
            "Often useful for displaying to users."
        ),
    )
    last_payment_error = JSONField(
        null=True,
        blank=True,
        help_text=(
            "The payment error encountered in the previous PaymentIntent confirmation."
        ),
    )
    next_action = JSONField(
        null=True,
        blank=True,
        help_text=(
            "If present, this property tells you what actions you need to take "
            "in order for your customer to fulfill a payment using the provided source."
        ),
    )
    on_behalf_of = StripeForeignKey(
        "Account",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="The account (if any) for which the funds of the "
        "PaymentIntent are intended.",
        related_name="payment_intents",
    )
    payment_method = StripeForeignKey(
        "PaymentMethod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Payment method used in this PaymentIntent.",
    )
    payment_method_types = JSONField(
        help_text=(
            "The list of payment method types (e.g. card) that this "
            "PaymentIntent is allowed to use."
        )
    )
    receipt_email = models.CharField(
        blank=True,
        max_length=255,
        help_text=(
            "Email address that the receipt for the resulting payment will be sent to."
        ),
    )
    # TODO: Add `review` field after we add Review model.
    setup_future_usage = StripeEnumField(
        enum=enums.IntentUsage,
        null=True,
        blank=True,
        help_text=(
            "Indicates that you intend to make future payments with this "
            "PaymentIntent’s payment method. "
            "If present, the payment method used with this PaymentIntent can "
            "be attached to a Customer, even after the transaction completes. "
            "Use `on_session` if you intend to only reuse the payment method "
            "when your customer is present in your checkout flow. Use `off_session` "
            "if your customer may or may not be in your checkout flow. "
            "Stripe uses `setup_future_usage` to dynamically optimize "
            "your payment flow and comply with regional legislation and network rules. "
            "For example, if your customer is impacted by SCA, using `off_session` "
            "will ensure that they are authenticated while processing this "
            "PaymentIntent. You will then be able to make later off-session payments "
            "for this customer."
        ),
    )
    shipping = JSONField(
        null=True, blank=True, help_text="Shipping information for this PaymentIntent."
    )
    statement_descriptor = models.CharField(
        max_length=22,
        blank=True,
        help_text=(
            "For non-card charges, you can use this value as the complete description "
            "that appears on your customers’ statements. Must contain at least one "
            "letter, maximum 22 characters."
        ),
    )
    status = StripeEnumField(
        enum=enums.PaymentIntentStatus,
        help_text=(
            "Status of this PaymentIntent, one of requires_payment_method, "
            "requires_confirmation, requires_action, processing, requires_capture, "
            "canceled, or succeeded. "
            "You can read more about PaymentIntent statuses here."
        ),
    )
    transfer_data = JSONField(
        null=True,
        blank=True,
        help_text=(
            "The data with which to automatically create a Transfer when the payment "
            "is finalized. "
            "See the PaymentIntents Connect usage guide for details."
        ),
    )
    transfer_group = models.CharField(
        blank=True,
        max_length=255,
        help_text=(
            "A string that identifies the resulting payment as part of a group. "
            "See the PaymentIntents Connect usage guide for details."
        ),
    )

    def update(self, api_key=None, **kwargs):
        """
        Call the stripe API's modify operation for this model

        :param api_key: The api key to use for this request.
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """
        api_key = api_key or self.default_api_key

        return self.api_retrieve(api_key=api_key).modify(**kwargs)

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

    Stripe documentation: https://stripe.com/docs/api#setup_intents
    """

    stripe_class = stripe.SetupIntent

    application = models.CharField(
        max_length=255,
        blank=True,
        help_text="ID of the Connect application that created the SetupIntent.",
    )
    cancellation_reason = StripeEnumField(
        enum=enums.SetupIntentCancellationReason,
        blank=True,
        help_text=(
            "Reason for cancellation of this SetupIntent, one of abandoned, "
            "requested_by_customer, or duplicate"
        ),
    )
    client_secret = models.TextField(
        max_length=5000,
        blank=True,
        help_text=(
            "The client secret of this SetupIntent. "
            "Used for client-side retrieval using a publishable key."
        ),
    )
    customer = StripeForeignKey(
        "Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Customer this SetupIntent belongs to, if one exists.",
    )
    last_setup_error = JSONField(
        null=True,
        blank=True,
        help_text="The error encountered in the previous SetupIntent confirmation.",
    )
    next_action = JSONField(
        null=True,
        blank=True,
        help_text=(
            "If present, this property tells you what actions you need to take in"
            "order for your customer to continue payment setup."
        ),
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
    payment_method_types = JSONField(
        help_text=(
            "The list of payment method types (e.g. card) that this PaymentIntent is "
            "allowed to use."
        )
    )
    status = StripeEnumField(
        enum=enums.SetupIntentStatus,
        help_text=(
            "Status of this SetupIntent, one of requires_payment_method, "
            "requires_confirmation, requires_action, processing, "
            "canceled, or succeeded."
        ),
    )
    usage = StripeEnumField(
        enum=enums.IntentUsage,
        default=enums.IntentUsage.off_session,
        help_text=(
            "Indicates how the payment method is intended to be used in the future."
        ),
    )


class Payout(StripeModel):
    """
    A Payout object is created when you receive funds from Stripe, or when you initiate
    a payout to either a bank account or debit card of a connected Stripe account.

    Stripe documentation: https://stripe.com/docs/api#payouts
    """

    expand_fields = ["destination"]
    stripe_class = stripe.Payout
    stripe_dashboard_item_name = "payouts"

    amount = StripeDecimalCurrencyAmountField(
        help_text="Amount (as decimal) to be transferred to your bank account or "
        "debit card."
    )
    arrival_date = StripeDateTimeField(
        help_text=(
            "Date the payout is expected to arrive in the bank. "
            "This factors in delays like weekends or bank holidays."
        )
    )
    automatic = models.BooleanField(
        help_text=(
            "`true` if the payout was created by an automated payout schedule, "
            "and `false` if it was requested manually."
        )
    )
    balance_transaction = StripeForeignKey(
        "BalanceTransaction",
        on_delete=models.SET_NULL,
        null=True,
        help_text="Balance transaction that describes the impact on your "
        "account balance.",
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
    failure_code = StripeEnumField(
        enum=enums.PayoutFailureCode,
        default="",
        blank=True,
        help_text=(
            "Error code explaining reason for transfer failure if available. "
            "See https://stripe.com/docs/api/python#transfer_failures."
        ),
    )
    failure_message = models.TextField(
        default="",
        blank=True,
        help_text=(
            "Message to user further explaining reason for "
            "payout failure if available."
        ),
    )
    method = StripeEnumField(
        max_length=8,
        enum=enums.PayoutMethod,
        help_text=(
            "The method used to send this payout. "
            "`instant` is only supported for payouts to debit cards."
        ),
    )
    # TODO: `original_payout` impl as OneToOne, with `reversed_by` reverse relation
    # original_payout = StripeForeignKey(
    #     "Payout",
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     help_text="If the payout reverses another, this is the original payout.",
    # )
    source_type = StripeEnumField(
        enum=enums.PayoutSourceType,
        help_text="The source balance this payout came from.",
    )
    statement_descriptor = models.CharField(
        max_length=255,
        default="",
        blank=True,
        help_text="Extra information about a payout to be displayed "
        "on the user's bank statement.",
    )
    status = StripeEnumField(
        enum=enums.PayoutStatus,
        help_text=(
            "Current status of the payout. "
            "A payout will be `pending` until it is submitted to the bank, "
            "at which point it becomes `in_transit`. "
            "It will then change to paid if the transaction goes through. "
            "If it does not go through successfully, "
            "its status will change to `failed` or `canceled`."
        ),
    )
    type = StripeEnumField(enum=enums.PayoutType)


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
    expand_fields = ["tiers"]
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
    recurring = JSONField(
        default=None,
        blank=True,
        null=True,
        help_text=(
            "The recurring components of a price such as `interval` and `usage_type`."
        ),
    )
    type = StripeEnumField(
        enum=enums.PriceType,
        help_text=(
            "Whether the price is for a one-time purchase or a recurring "
            "(subscription) purchase."
        ),
    )
    unit_amount = StripeQuantumCurrencyAmountField(
        null=True,
        blank=True,
        help_text=(
            "The unit amount in cents to be charged, represented as a whole "
            "integer if possible. Null if a sub-cent precision is required."
        ),
    )
    unit_amount_decimal = StripeDecimalCurrencyAmountField(
        null=True,
        blank=True,
        max_digits=19,
        decimal_places=12,
        help_text=(
            "The unit amount in cents to be charged, represented as a decimal "
            "string with at most 12 decimal places."
        ),
    )

    # More attributes…
    billing_scheme = StripeEnumField(
        enum=enums.BillingScheme,
        blank=True,
        help_text=(
            "Describes how to compute the price per period. "
            "Either `per_unit` or `tiered`. "
            "`per_unit` indicates that the fixed amount (specified in `unit_amount` "
            "or `unit_amount_decimal`) will be charged per unit in `quantity` "
            "(for prices with `usage_type=licensed`), or per unit of total "
            "usage (for prices with `usage_type=metered`). "
            "`tiered` indicates that the unit pricing will be computed using "
            "a tiering strategy as defined using the `tiers` and `tiers_mode` "
            "attributes."
        ),
    )
    lookup_key = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="A lookup key used to retrieve prices dynamically from a "
        "static string.",
    )
    tiers = JSONField(
        null=True,
        blank=True,
        help_text=(
            "Each element represents a pricing tier. "
            "This parameter requires `billing_scheme` to be set to `tiered`."
        ),
    )
    tiers_mode = StripeEnumField(
        enum=enums.PriceTiersMode,
        null=True,
        blank=True,
        help_text=(
            "Defines if the tiering price should be `graduated` or `volume` based. "
            "In `volume`-based tiering, the maximum quantity within a period "
            "determines the per unit price, in `graduated` tiering pricing can "
            "successively change as the quantity grows."
        ),
    )
    transform_quantity = JSONField(
        null=True,
        blank=True,
        help_text=(
            "Apply a transformation to the reported usage or set quantity "
            "before computing the amount billed. Cannot be combined with `tiers`."
        ),
    )

    class Meta(object):
        ordering = ["unit_amount"]

    @classmethod
    def get_or_create(cls, **kwargs):
        """ Get or create a Price."""

        try:
            return Price.objects.get(id=kwargs["id"]), False
        except Price.DoesNotExist:
            return cls.create(**kwargs), True

    @classmethod
    def create(cls, **kwargs):
        # A few minor things are changed in the api-version of the create call
        api_kwargs = dict(kwargs)
        api_kwargs["unit_amount"] = int(api_kwargs["unit_amount"] * 100)

        if isinstance(api_kwargs.get("product"), StripeModel):
            api_kwargs["product"] = api_kwargs["product"].id

        stripe_price = cls._api_create(**api_kwargs)
        price = cls.sync_from_stripe_data(stripe_price)

        return price

    def __str__(self):
        return self.nickname or self.id

    @property
    def human_readable_price(self):
        amount = get_friendly_currency_amount(self.unit_amount / 100, self.currency)
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
                template = _("{amount} every {interval_count} {interval}")
                format_args["interval"] = interval
                format_args["interval_count"] = interval_count
        else:
            template = _("{amount} (one time)")

        return format_lazy(template, **format_args)


class Refund(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/api#refund_object
    """

    stripe_class = stripe.Refund

    amount = StripeQuantumCurrencyAmountField(help_text="Amount, in cents.")
    balance_transaction = StripeForeignKey(
        "BalanceTransaction",
        on_delete=models.SET_NULL,
        null=True,
        help_text="Balance transaction that describes the impact on your account "
        "balance.",
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
        help_text="If the refund failed, this balance transaction describes the "
        "adjustment made on your account balance that reverses the initial "
        "balance transaction.",
    )
    failure_reason = StripeEnumField(
        enum=enums.RefundFailureReason,
        default="",
        blank=True,
        help_text="If the refund failed, the reason for refund failure if known.",
    )
    reason = StripeEnumField(
        enum=enums.RefundReason,
        blank=True,
        default="",
        help_text="Reason for the refund.",
    )
    receipt_number = models.CharField(
        max_length=9,
        default="",
        blank=True,
        help_text="The transaction number that appears on email receipts sent "
        "for this charge.",
    )
    status = StripeEnumField(
        blank=True, enum=enums.RefundStatus, help_text="Status of the refund."
    )

    def get_stripe_dashboard_url(self):
        return self.charge.get_stripe_dashboard_url()
