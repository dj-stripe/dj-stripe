import logging
import warnings
from typing import Optional, Union

import stripe
from django.db import models
from django.utils import timezone
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from stripe import InvalidRequestError

from .. import enums
from ..fields import (
    JSONField,
    StripeDateTimeField,
    StripeEnumField,
    StripeForeignKey,
    StripeIdField,
)
from ..managers import SubscriptionManager
from ..settings import djstripe_settings
from ..utils import QuerySetMock, get_friendly_currency_amount
from .base import StripeModel

logger = logging.getLogger(__name__)


class Coupon(StripeModel):
    """
    A coupon contains information about a percent-off or amount-off discount you might want to apply to a customer.
    Coupons may be applied to invoices or orders.
    Coupons do not work with conventional one-off charges.

    Stripe documentation: https://stripe.com/docs/api/coupons?lang=python
    """

    stripe_class = stripe.Coupon
    expand_fields = ["applies_to"]
    stripe_dashboard_item_name = "coupons"

    # Critical fields to keep
    id = StripeIdField(max_length=500)

    # Property accessors for commonly used fields
    @property
    def applies_to(self):
        return self.stripe_data.get("applies_to")

    @property
    def amount_off(self):
        return self.stripe_data.get("amount_off")

    @property
    def currency(self):
        return self.stripe_data.get("currency")

    @property
    def duration(self):
        return self.stripe_data.get("duration")

    @property
    def duration_in_months(self):
        return self.stripe_data.get("duration_in_months")

    @property
    def max_redemptions(self):
        return self.stripe_data.get("max_redemptions")

    @property
    def name(self):
        return self.stripe_data.get("name")

    @property
    def percent_off(self):
        return self.stripe_data.get("percent_off")

    @property
    def redeem_by(self):
        return self.stripe_data.get("redeem_by")

    @property
    def times_redeemed(self):
        return self.stripe_data.get("times_redeemed", 0)

    class Meta(StripeModel.Meta):
        unique_together = ("id", "livemode")

    def __str__(self):
        name = self.stripe_data.get("name")
        if name:
            return name
        return self.human_readable

    @property
    def human_readable_amount(self):
        percent_off = self.stripe_data.get("percent_off")
        if percent_off:
            amount = f"{percent_off}%"
        elif self.stripe_data.get("currency"):
            amount = get_friendly_currency_amount(
                self.stripe_data.get("amount_off", 0), self.stripe_data.get("currency")
            )
        else:
            amount = "(invalid amount)"
        return f"{amount} off"

    @property
    def human_readable(self):
        duration = self.stripe_data.get("duration")
        if duration == "repeating":
            duration_in_months = self.stripe_data.get("duration_in_months")
            if duration_in_months == 1:
                duration = "for 1 month"
            else:
                duration = f"for {duration_in_months} months"
        return f"{self.human_readable_amount} {duration}"


class PromotionCode(StripeModel):
    """
    This is an object representing a Promotion Code.

    A Promotion Code represents a customer-redeemable code for a coupon.
    It can be used to create multiple codes for a single coupon.

    Stripe documentation: https://stripe.com/docs/api/promotion_codes?lang=python
    """

    stripe_class = stripe.PromotionCode

    # https://docs.stripe.com/api/promotion_codes/object#promotion_code_object-code
    @property
    def code(self) -> str:
        return self.stripe_data["code"]

    # https://docs.stripe.com/api/promotion_codes/object#promotion_code_object-active
    @property
    def active(self) -> str:
        return self.stripe_data["active"]

    # https://docs.stripe.com/api/promotion_codes/object#promotion_code_object-times_redeemed
    @property
    def times_redeemed(self) -> int:
        return self.stripe_data["times_redeemed"]

    # https://docs.stripe.com/api/promotion_codes/object#promotion_code_object-max_redemptions
    @property
    def max_redemptions(self) -> Optional[int]:
        return self.stripe_data.get("max_redemptions")


class Discount(StripeModel):
    """
    A discount represents the actual application of a coupon or promotion code.
    It contains information about when the discount began,
    when it will end, and what it is applied to.

    Stripe documentation: https://stripe.com/docs/api/discounts
    """

    expand_fields = ["customer"]
    stripe_class = None

    customer = StripeForeignKey(
        "Customer",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="The ID of the customer associated with this discount.",
        related_name="customer_discounts",
    )
    invoice = StripeForeignKey(
        "Invoice",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text=(
            "The invoice that the discount’s coupon was applied to, if it was applied"
            " directly to a particular invoice."
        ),
        related_name="invoice_discounts",
    )
    promotion_code = models.CharField(
        max_length=255,
        blank=True,
        help_text="The promotion code applied to create this discount.",
    )
    subscription = StripeForeignKey(
        "subscription",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text=(
            "The subscription that this coupon is applied to, if it is applied to a"
            " particular subscription."
        ),
        related_name="subscription_discounts",
    )

    @classmethod
    def is_valid_object(cls, data):
        """
        Returns whether the data is a valid object for the class
        """
        return "object" in data and data["object"] == "discount"


class BaseInvoice(StripeModel):
    """
    The abstract base model shared by Invoice and UpcomingInvoice

    Note:
    Most fields are defined on BaseInvoice so they're available to both models.
    ManyToManyFields are an exception, since UpcomingInvoice doesn't exist in the db.
    """

    stripe_class = stripe.Invoice
    stripe_dashboard_item_name = "invoices"
    expand_fields = ["discounts", "lines.data.discounts"]

    charge = models.OneToOneField(
        "Charge",
        on_delete=models.CASCADE,
        null=True,
        # we need to use the %(class)s placeholder to avoid related name
        # clashes between Invoice and UpcomingInvoice
        related_name="latest_%(class)s",
        help_text="The latest charge generated for this invoice, if any.",
    )
    # Critical fields to keep
    customer = StripeForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        # we need to use the %(class)s placeholder to avoid related name
        # clashes between Invoice and UpcomingInvoice
        related_name="%(class)ss",
        help_text="The customer associated with this invoice.",
    )
    default_payment_method = StripeForeignKey(
        "PaymentMethod",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=(
            "Default payment method for the invoice. It must belong to the "
            "customer associated with the invoice. If not set, defaults to the "
            "subscription's default payment method, if any, or to the default payment "
            "method in the customer's invoice settings."
        ),
    )
    payment_intent = models.OneToOneField(
        "PaymentIntent",
        on_delete=models.CASCADE,
        null=True,
        help_text=(
            "The PaymentIntent associated with this invoice. "
            "The PaymentIntent is generated when the invoice is finalized, "
            "and can then be used to pay the invoice."
            "Note that voiding an invoice will cancel the PaymentIntent"
        ),
    )
    subscription = StripeForeignKey(
        "Subscription",
        null=True,
        # we need to use the %(class)s placeholder to avoid related name
        # clashes between Invoice and UpcomingInvoice
        related_name="%(class)ss",
        on_delete=models.SET_NULL,
        help_text="The subscription that this invoice was prepared for, if any.",
    )

    # Property accessors for commonly used fields
    @property
    def currency(self):
        return self.stripe_data.get("currency")

    @property
    def due_date(self):
        return self.stripe_data.get("due_date")

    @property
    def number(self):
        return self.stripe_data.get("number")

    @property
    def period_end(self):
        return self.stripe_data.get("period_end")

    @property
    def period_start(self):
        return self.stripe_data.get("period_start")

    @property
    def receipt_number(self):
        return self.stripe_data.get("receipt_number")

    @property
    def status(self):
        return self.stripe_data.get("status")

    @property
    def subtotal(self):
        return self.stripe_data.get("subtotal")

    @property
    def tax(self):
        return self.stripe_data.get("tax")

    @property
    def tax_percent(self):
        return self.stripe_data.get("tax_percent")

    @property
    def total(self):
        return self.stripe_data.get("total")

    @property
    def discounts(self):
        """The discounts applied to the invoice."""
        return self.stripe_data.get("discounts")

    class Meta(StripeModel.Meta):
        abstract = True
        ordering = ["-created"]

    def __str__(self):
        invoice_number = (
            self.stripe_data.get("number")
            or self.stripe_data.get("receipt_number")
            or self.id
        )
        amount = get_friendly_currency_amount(
            self.stripe_data.get("amount_paid", 0), self.stripe_data.get("currency")
        )
        return (
            f"Invoice #{invoice_number} for {amount} ({self.stripe_data.get('status')})"
        )

    @classmethod
    def upcoming(
        cls,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
        customer=None,
        subscription=None,
        subscription_plan=None,
        **kwargs,
    ) -> Optional["UpcomingInvoice"]:
        """
        Gets the upcoming preview invoice (singular) for a customer.

        At any time, you can preview the upcoming
        invoice for a customer. This will show you all the charges that are
        pending, including subscription renewal charges, invoice item charges,
        etc. It will also show you any discount that is applicable to the
        customer. (Source: https://stripe.com/docs/api#upcoming_invoice)

        .. important:: Note that when you are viewing an upcoming invoice,
            you are simply viewing a preview.

        :param customer: The identifier of the customer whose upcoming invoice \
        you'd like to retrieve.
        :type customer: Customer or string (customer ID)
        :param coupon: The code of the coupon to apply.
        :type coupon: str
        :param subscription: The identifier of the subscription to retrieve an \
        invoice for.
        :type subscription: Subscription or string (subscription ID)
        :param subscription_plan: If set, the invoice returned will preview \
        updating the subscription given to this plan, or creating a new \
        subscription to this plan if no subscription is given.
        :type subscription_plan: Plan or string (plan ID)
        """

        # Convert Customer to id
        if customer is not None and isinstance(customer, StripeModel):
            customer = customer.id

        # Convert Subscription to id
        if subscription is not None and isinstance(subscription, StripeModel):
            subscription = subscription.id

        # Convert Plan to id
        if subscription_plan is not None and isinstance(subscription_plan, StripeModel):
            subscription_plan = subscription_plan.id

        try:
            upcoming_stripe_invoice = cls.stripe_class.upcoming(
                api_key=api_key,
                customer=customer,
                subscription=subscription,
                subscription_plan=subscription_plan,
                stripe_version=djstripe_settings.STRIPE_API_VERSION,
                **kwargs,
            )
        except InvalidRequestError as exc:
            if str(exc) != "Nothing to invoice for customer":
                raise
            return None

        # Workaround for "id" being missing (upcoming invoices don't persist).
        upcoming_stripe_invoice["id"] = "upcoming"

        return UpcomingInvoice._create_from_stripe_object(
            upcoming_stripe_invoice,
            save=False,
            api_key=api_key,
        )

    def retry(self, **kwargs):
        """Retry payment on this invoice if it isn't paid."""

        if self.status != enums.InvoiceStatus.paid:
            stripe_invoice = self.api_retrieve()
            updated_stripe_invoice = stripe_invoice.pay(
                **kwargs
            )  # pay() throws an exception if the charge is not successful.
            type(self).sync_from_stripe_data(
                updated_stripe_invoice, api_key=self.default_api_key
            )
            return True
        return False

    def _attach_objects_post_save_hook(
        self,
        cls,
        data,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
        pending_relations=None,
    ):
        super()._attach_objects_post_save_hook(
            cls, data, api_key=api_key, pending_relations=pending_relations
        )

        # LineItems need a saved invoice because they're associated via a
        # RelatedManager, so this must be done as part of the post save hook.
        try:
            self._lineitems = cls._stripe_object_to_line_items(
                target_cls=LineItem, data=data, invoice=self, api_key=api_key
            )
        except Exception:
            # subscription items (si_) can sometimes not exist at all in Stripe despite
            # their ID showing up as part of the webhook data.
            # safe to ignore -- subscription_item will then be null, there's nothing we can do.
            pass

        # sync every discount
        if self.discounts:
            for discount in self.discounts:
                if discount:
                    Discount.sync_from_stripe_data(discount, api_key=api_key)

        for line in data.get("lines", []):
            invoice_item_data = line.get("invoice_item")
            if invoice_item_data:
                InvoiceItem.sync_from_stripe_data(invoice_item_data, api_key=api_key)

    @property
    def amount_due(self) -> int:
        return self.stripe_data["amount_due"]

    @property
    def attempt_count(self) -> int:
        return self.stripe_data["attempt_count"]

    @property
    def billing_reason(self) -> str:
        return self.stripe_data["billing_reason"]

    @property
    def hosted_invoice_url(self) -> str:
        return self.stripe_data["hosted_invoice_url"]

    @property
    def invoice_pdf(self) -> str:
        return self.stripe_data["invoice_pdf"]

    @property
    def paid(self) -> bool:
        return self.stripe_data["paid"]

    @property
    def footer(self) -> str:
        return self.stripe_data["footer"]

    @property
    def webhooks_delivered_at(self) -> int | None:
        """
        The date and time the invoice was last attempted to be paid.
        This is the time when the last webhook was successfully sent.
        """
        return self.stripe_data.get("webhooks_delivered_at")


class Invoice(BaseInvoice):
    """
    Invoices are statements of what a customer owes for a particular billing
    period, including subscriptions, invoice items, and any automatic proration
    adjustments if necessary.

    Once an invoice is created, payment is automatically attempted. Note that
    the payment, while automatic, does not happen exactly at the time of invoice
    creation. If you have configured webhooks, the invoice will wait until one
    hour after the last webhook is successfully sent (or the last webhook times
    out after failing).

    Any customer credit on the account is applied before determining how much is
    due for that invoice (the amount that will be actually charged).
    If the amount due for the invoice is less than 50 cents (the minimum for a
    charge), we add the amount to the customer's running account balance to be
    added to the next invoice. If this amount is negative, it will act as a
    credit to offset the next invoice. Note that the customer account balance
    does not include unpaid invoices; it only includes balances that need to be
    taken into account when calculating the amount due for the next invoice.

    Stripe documentation: https://stripe.com/docs/api?lang=python#invoices
    """

    # Note:
    # Most fields are defined on BaseInvoice so they're shared with UpcomingInvoice.
    # ManyToManyFields are an exception, since UpcomingInvoice doesn't exist in the db.
    default_tax_rates = models.ManyToManyField(
        "TaxRate",
        # explicitly specify the joining table name as though the joining model
        # was defined with through="DjstripeInvoiceDefaultTaxRate"
        db_table="djstripe_djstripeinvoicedefaulttaxrate",
        related_name="+",
        blank=True,
        help_text="The tax rates applied to this invoice, if any.",
    )


class UpcomingInvoice(BaseInvoice):
    """
    The preview of an upcoming invoice - does not exist in the Django database.

    See BaseInvoice.upcoming()

    Logically it should be set abstract, but that doesn't quite work since we
    do actually want to instantiate the model and use relations.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._lineitems = []
        self._default_tax_rates = []

    def get_stripe_dashboard_url(self):
        return ""

    def _attach_objects_hook(
        self, cls, data, api_key=djstripe_settings.STRIPE_SECRET_KEY, current_ids=None
    ):
        super()._attach_objects_hook(
            cls, data, api_key=api_key, current_ids=current_ids
        )

        self._lineitems = cls._stripe_object_to_line_items(
            target_cls=LineItem, data=data, invoice=self, api_key=api_key
        )

    def _attach_objects_post_save_hook(
        self,
        cls,
        data,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
        pending_relations=None,
    ):
        super()._attach_objects_post_save_hook(
            cls, data, api_key=api_key, pending_relations=pending_relations
        )

        self._default_tax_rates = cls._stripe_object_to_default_tax_rates(
            target_cls=TaxRate, data=data, api_key=api_key
        )

    @property
    def invoiceitems(self):
        """
        Gets the invoice items associated with this upcoming invoice.

        This differs from normal (non-upcoming) invoices, in that upcoming
        invoices are in-memory and do not persist to the database. Therefore,
        all of the data comes from the Stripe API itself.

        Instead of returning a normal queryset for the invoiceitems, this will
        return a mock of a queryset, but with the data fetched from Stripe - It
        will act like a normal queryset, but mutation will silently fail.
        """
        # filter lineitems with type="invoice_item" and fetch all the actual InvoiceItem objects
        items = [
            item.invoice_item for item in self._lineitems if item.type == "invoice_item"
        ]

        return QuerySetMock.from_iterable(InvoiceItem, items)

    @property
    def lineitems(self):
        """
        Gets the line items associated with this upcoming invoice.

        This differs from normal (non-upcoming) invoices, in that upcoming
        invoices are in-memory and do not persist to the database. Therefore,
        all of the data comes from the Stripe API itself.

        Instead of returning a normal queryset for the lineitems, this will
        return a mock of a queryset, but with the data fetched from Stripe - It
        will act like a normal queryset, but mutation will silently fail.
        """
        return QuerySetMock.from_iterable(LineItem, self._lineitems)

    @property
    def default_tax_rates(self):
        """
        Gets the default tax rates associated with this upcoming invoice.
        :return:
        """
        return QuerySetMock.from_iterable(TaxRate, self._default_tax_rates)

    @property
    def id(self):
        return None

    @id.setter
    def id(self, value):
        return  # noop

    def save(self, *args, **kwargs):
        return  # noop


class InvoiceItem(StripeModel):
    """
    Sometimes you want to add a charge or credit to a customer but only actually
    charge the customer's card at the end of a regular billing cycle.
    This is useful for combining several charges to minimize per-transaction fees
    or having Stripe tabulate your usage-based billing totals.

    Stripe documentation: https://stripe.com/docs/api?lang=python#invoiceitems
    """

    stripe_class = stripe.InvoiceItem
    expand_fields = ["discounts"]

    # Foreign keys remain as model fields
    customer = StripeForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        related_name="invoiceitems",
        help_text="The customer associated with this invoiceitem.",
    )
    # Fields converted to properties - see below
    invoice = StripeForeignKey(
        "Invoice",
        on_delete=models.CASCADE,
        null=True,
        related_name="invoiceitems",
        help_text="The invoice to which this invoiceitem is attached.",
    )
    # Period fields converted to properties - see below
    plan = models.ForeignKey(
        "Plan",
        null=True,
        on_delete=models.SET_NULL,
        help_text=(
            "If the invoice item is a proration, the plan of the subscription "
            "for which the proration was computed."
        ),
    )
    price = models.ForeignKey(
        "Price",
        null=True,
        related_name="invoiceitems",
        on_delete=models.SET_NULL,
        help_text=(
            "If the invoice item is a proration, the price of the subscription "
            "for which the proration was computed."
        ),
    )
    # Proration and quantity fields converted to properties - see below
    subscription = StripeForeignKey(
        "Subscription",
        null=True,
        related_name="invoiceitems",
        on_delete=models.SET_NULL,
        help_text=(
            "The subscription that this invoice item has been created for, if any."
        ),
    )
    # XXX: subscription_item
    tax_rates = models.ManyToManyField(
        "TaxRate",
        # explicitly specify the joining table name as though the joining model
        # was defined with through="DjstripeInvoiceItemTaxRate"
        db_table="djstripe_djstripeinvoiceitemtaxrate",
        related_name="+",
        blank=True,
        help_text=(
            "The tax rates which apply to this invoice item. When set, "
            "the default_tax_rates on the invoice do not apply to this "
            "invoice item."
        ),
    )
    # Unit amount fields converted to properties - see below

    # Properties replacing field definitions
    @property
    def amount(self):
        """Amount invoiced (as decimal)."""
        return self.stripe_data.get("amount")

    @property
    def currency(self):
        """Currency code."""
        return self.stripe_data.get("currency")

    @property
    def date(self):
        """The date on the invoiceitem."""
        return self.stripe_data.get("date")

    @property
    def discountable(self):
        """If True, discounts will apply to this invoice item. Always False for prorations."""
        return self.stripe_data.get("discountable", False)

    @property
    def discounts(self):
        """The discounts which apply to the invoice item. Item discounts are applied before invoice discounts."""
        return self.stripe_data.get("discounts")

    @property
    def period(self):
        """Period information."""
        return self.stripe_data.get("period", {})

    @property
    def period_end(self):
        """Might be the date when this invoiceitem's invoice was sent."""
        return self.stripe_data.get("period_end")

    @property
    def period_start(self):
        """Might be the date when this invoiceitem was added to the invoice."""
        return self.stripe_data.get("period_start")

    @property
    def proration(self):
        """Whether or not the invoice item was created automatically as a proration adjustment when the customer switched plans."""
        return self.stripe_data.get("proration", False)

    @property
    def quantity(self):
        """If the invoice item is a proration, the quantity of the subscription for which the proration was computed."""
        return self.stripe_data.get("quantity")

    @property
    def unit_amount(self):
        """Unit amount (in the currency specified) of the invoice item."""
        return self.stripe_data.get("unit_amount")

    @property
    def unit_amount_decimal(self):
        """Same as unit_amount, but contains a decimal value with at most 12 decimal places."""
        return self.stripe_data.get("unit_amount_decimal")

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        data["period_start"] = data["period"]["start"]
        data["period_end"] = data["period"]["end"]

        return data

    def _attach_objects_post_save_hook(
        self,
        cls,
        data,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
        pending_relations=None,
    ):
        super()._attach_objects_post_save_hook(
            cls, data, api_key=api_key, pending_relations=pending_relations
        )

        if self.pk:
            # only call .set() on saved instance (ie don't on items of UpcomingInvoice)
            self.tax_rates.set(
                cls._stripe_object_to_tax_rates(
                    target_cls=TaxRate, data=data, api_key=api_key
                )
            )

        # sync every discount
        for discount in self.discounts:
            Discount.sync_from_stripe_data(discount, api_key=api_key)

    def __str__(self):
        return self.description

    def get_stripe_dashboard_url(self):
        return self.invoice.get_stripe_dashboard_url()

    def api_retrieve(self, *args, **kwargs):
        if "-il_" in self.id:
            warnings.warn(
                f"Attempting to retrieve InvoiceItem with id={self.id!r}"
                " will most likely fail. "
                "Run manage.py djstripe_update_invoiceitem_ids if this is a problem."
            )

        return super().api_retrieve(*args, **kwargs)


class LineItem(StripeModel):
    """
    The individual line items that make up the invoice.

    Stripe documentation: https://stripe.com/docs/api/invoices/line_item
    """

    stripe_class = stripe.InvoiceLineItem
    expand_fields = ["discounts"]

    # Foreign keys remain as model fields
    invoice_item = StripeForeignKey(
        "InvoiceItem",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="The ID of the invoice item associated with this line item if any.",
    )
    # Fields converted to properties - see below
    subscription = StripeForeignKey(
        "Subscription",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="The subscription that the invoice item pertains to, if any.",
    )
    subscription_item = StripeForeignKey(
        "SubscriptionItem",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text=(
            "The subscription item that generated this invoice item. Left empty if the"
            " line item is not an explicit result of a subscription."
        ),
    )
    # Tax and other fields converted to properties - see below

    # Properties replacing field definitions
    @property
    def amount(self):
        """The amount, in cents."""
        return self.stripe_data.get("amount")

    @property
    def amount_excluding_tax(self):
        """The integer amount in cents representing the amount for this line item, excluding all tax and discounts."""
        return self.stripe_data.get("amount_excluding_tax")

    @property
    def currency(self):
        """Currency code."""
        return self.stripe_data.get("currency")

    @property
    def discount_amounts(self):
        """The amount of discount calculated per discount for this line item."""
        return self.stripe_data.get("discount_amounts")

    @property
    def discountable(self):
        """If True, discounts will apply to this line item. Always False for prorations."""
        return self.stripe_data.get("discountable", False)

    @property
    def discounts(self):
        """The discounts applied to the invoice line item. Line item discounts are applied before invoice discounts."""
        return self.stripe_data.get("discounts")

    @property
    def period(self):
        """The period this line_item covers."""
        return self.stripe_data.get("period", {})

    @property
    def period_end(self):
        """The end of the period, which must be greater than or equal to the start."""
        return self.stripe_data.get("period_end")

    @property
    def period_start(self):
        """The start of the period."""
        return self.stripe_data.get("period_start")

    @property
    def price(self):
        """The price of the line item."""
        return self.stripe_data.get("price")

    @property
    def proration(self):
        """Whether or not the invoice item was created automatically as a proration adjustment when the customer switched plans."""
        return self.stripe_data.get("proration", False)

    @property
    def proration_details(self):
        """Additional details for proration line items."""
        return self.stripe_data.get("proration_details")

    @property
    def tax_amounts(self):
        """The amount of tax calculated per tax rate for this line item."""
        return self.stripe_data.get("tax_amounts")

    @property
    def tax_rates(self):
        """The tax rates which apply to the line item."""
        return self.stripe_data.get("tax_rates")

    @property
    def type(self):
        """Type of line item."""
        return self.stripe_data.get("type")

    @property
    def unit_amount_excluding_tax(self):
        """The amount in cents representing the unit amount for this line item, excluding all tax and discounts."""
        return self.stripe_data.get("unit_amount_excluding_tax")

    @property
    def quantity(self):
        """The quantity of the subscription, if the line item is a subscription or a proration."""
        return self.stripe_data.get("quantity")

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        data["period_start"] = data["period"]["start"]
        data["period_end"] = data["period"]["end"]

        return data

    def _attach_objects_post_save_hook(
        self,
        cls,
        data,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
        pending_relations=None,
    ):
        super()._attach_objects_post_save_hook(
            cls, data, api_key=api_key, pending_relations=pending_relations
        )

        # sync every discount
        for discount in self.discounts:
            Discount.sync_from_stripe_data(discount, api_key=api_key)

    @classmethod
    def api_list(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        """
        Call the stripe API's list operation for this model.
        Note that we only iterate and sync the LineItem associated with the
        passed in Invoice.

        Upcoming invoices are virtual and are not saved and hence their
        line items are also not retrieved and synced

        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string

        See Stripe documentation for accepted kwargs for each object.

        :returns: an iterator over all items in the query
        """
        # Update kwargs with `expand` param
        kwargs = cls.get_expand_params(api_key, **kwargs)

        # get current invoice if any
        invoice_id = kwargs.pop("id")

        # get expand parameter that needs to be passed to invoice.lines.list call
        expand_fields = kwargs.pop("expand")

        invoice = Invoice.stripe_class.retrieve(invoice_id, api_key=api_key, **kwargs)

        # iterate over all the line items on the current invoice
        return invoice.lines.list(
            api_key=api_key, expand=expand_fields, **kwargs
        ).auto_paging_iter()


class Plan(StripeModel):
    """
    A subscription plan contains the pricing information for different
    products and feature levels on your site.

    Stripe documentation: https://stripe.com/docs/api/plans?lang=python

    NOTE: The Stripe Plans API has been deprecated in favor of the Prices API.
    You may want to upgrade to use the Price model instead of the Plan model.
    """

    stripe_class = stripe.Plan
    expand_fields = ["product", "tiers"]
    stripe_dashboard_item_name = "plans"

    # Properties for Plan model fields
    @property
    def active(self):
        """Whether the plan is currently available for new subscriptions."""
        return self.stripe_data.get("active", True)

    @property
    def aggregate_usage(self):
        """Specifies a usage aggregation strategy for plans of `usage_type=metered`."""
        return self.stripe_data.get("aggregate_usage")

    @property
    def amount(self):
        """The amount in cents to be charged on the interval specified."""
        return self.stripe_data.get("amount")

    @property
    def amount_decimal(self):
        """Same as `amount`, but contains a decimal value with at most 12 decimal places."""
        return self.stripe_data.get("amount_decimal")

    @property
    def billing_scheme(self):
        """Describes how to compute the price per period. Either `per_unit` or `tiered`."""
        return self.stripe_data.get("billing_scheme", "per_unit")

    @property
    def currency(self):
        """Three-letter ISO currency code."""
        return self.stripe_data.get("currency")

    @property
    def interval(self):
        """The frequency at which a subscription is billed. One of `day`, `week`, `month` or `year`."""
        return self.stripe_data.get("interval")

    @property
    def interval_count(self):
        """The number of intervals between subscription billings."""
        return self.stripe_data.get("interval_count", 1)

    @property
    def nickname(self):
        """A brief description of the plan, hidden from customers."""
        return self.stripe_data.get("nickname")

    @property
    def product(self):
        """The product whose pricing this plan determines."""
        return self.stripe_data.get("product")

    @property
    def tiers(self):
        """Each element represents a pricing tier."""
        return self.stripe_data.get("tiers", [])

    @property
    def tiers_mode(self):
        """Defines if the tiering price should be `graduated` or `volume` based."""
        return self.stripe_data.get("tiers_mode")

    @property
    def transform_usage(self):
        """Apply a transformation to the reported usage or set quantity."""
        return self.stripe_data.get("transform_usage")

    @property
    def trial_period_days(self):
        """Number of trial period days granted when subscribing a customer to this plan."""
        return self.stripe_data.get("trial_period_days")

    @property
    def usage_type(self):
        """Configures how the quantity per period should be determined."""
        return self.stripe_data.get("usage_type", "licensed")

    @classmethod
    def get_or_create(cls, **kwargs):
        """Get or create a Plan."""

        try:
            return cls.objects.get(id=kwargs["id"]), False
        except cls.DoesNotExist:
            return cls.create(**kwargs), True

    @classmethod
    def create(cls, **kwargs):
        # A few minor things are changed in the api-version of the create call
        api_kwargs = kwargs.copy()
        api_kwargs["amount"] = int(api_kwargs["amount"] * 100)

        if isinstance(api_kwargs.get("product"), StripeModel):
            api_kwargs["product"] = api_kwargs["product"].id

        stripe_plan = cls._api_create(**api_kwargs)
        api_key = api_kwargs.get("api_key") or djstripe_settings.STRIPE_SECRET_KEY
        plan = cls.sync_from_stripe_data(stripe_plan, api_key=api_key)

        return plan

    def __str__(self):
        product = self.product
        if product and isinstance(product, dict) and product.get("name"):
            name = product.get("name")
            return f"{self.human_readable_price} for {name}"
        return self.human_readable_price

    @property
    def amount_in_cents(self):
        return int(self.amount * 100)

    @property
    def human_readable_price(self) -> str:
        if self.billing_scheme == "per_unit":
            unit_amount = self.amount
            amount = get_friendly_currency_amount(unit_amount, self.currency)
        else:
            # tiered billing scheme
            tiers = self.tiers
            if not tiers:
                amount = "Tiered pricing"
            else:
                tier_1 = tiers[0]
                flat_amount_tier_1 = tier_1.get("flat_amount")
                unit_amount_tier_1 = tier_1.get("unit_amount", 0)
                formatted_unit_amount_tier_1 = get_friendly_currency_amount(
                    unit_amount_tier_1 / 100, self.currency
                )
                amount = f"Starts at {formatted_unit_amount_tier_1} per unit"

                if flat_amount_tier_1 is not None:
                    formatted_flat_amount_tier_1 = get_friendly_currency_amount(
                        flat_amount_tier_1 / 100, self.currency
                    )
                    amount = f"{amount} + {formatted_flat_amount_tier_1}"

        format_args = {"amount": amount}

        interval_count = self.interval_count
        if interval_count == 1:
            interval = {
                "day": _("day"),
                "week": _("week"),
                "month": _("month"),
                "year": _("year"),
            }[self.interval]
            template = _("{amount}/{interval}")
            format_args["interval"] = interval
        else:
            interval = {
                "day": _("days"),
                "week": _("weeks"),
                "month": _("months"),
                "year": _("years"),
            }[self.interval]
            template = _("{amount} / every {interval_count} {interval}")
            format_args["interval"] = interval
            format_args["interval_count"] = interval_count

        return str(format_lazy(template, **format_args))


class Subscription(StripeModel):
    """
    Subscriptions allow you to charge a customer's card on a recurring basis.
    A subscription ties a customer to a particular plan you've created.

    A subscription still in its trial period is ``trialing`` and moves to ``active``
    when the trial period is over.

    When payment to renew the subscription fails, the subscription becomes ``past_due``.
    After Stripe has exhausted all payment retry attempts, the subscription ends up
    with a status of either ``canceled`` or ``unpaid`` depending on your retry settings.

    Note that when a subscription has a status of ``unpaid``, no subsequent invoices
    will be attempted (invoices will be created, but then immediately
    automatically closed.

    Additionally, updating customer card details will not lead to Stripe retrying the
    latest invoice.).
    After receiving updated card details from a customer, you may choose to reopen and
    pay their closed invoices.

    Stripe documentation: https://stripe.com/docs/api?lang=python#subscriptions
    """

    stripe_class = stripe.Subscription
    stripe_dashboard_item_name = "subscriptions"

    customer = StripeForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        related_name="subscriptions",
        help_text="The customer associated with this subscription.",
    )

    objects = SubscriptionManager()

    # Properties for Subscription model fields
    @property
    def application_fee_percent(self):
        """A non-negative decimal between 0 and 100, with at most two decimal places."""
        return self.stripe_data.get("application_fee_percent")

    @property
    def automatic_tax(self):
        """Automatic tax settings for this subscription."""
        return self.stripe_data.get("automatic_tax", {})

    @property
    def billing_cycle_anchor(self):
        """Determines the date of the first full invoice."""
        return self.stripe_data.get("billing_cycle_anchor")

    @property
    def billing_thresholds(self):
        """Define thresholds at which an invoice will be sent."""
        return self.stripe_data.get("billing_thresholds")

    @property
    def cancel_at(self):
        """A date in the future at which the subscription will automatically get canceled."""
        return self.stripe_data.get("cancel_at")

    @property
    def cancel_at_period_end(self):
        """If the subscription has been canceled with the at_period_end flag set to true."""
        return self.stripe_data.get("cancel_at_period_end", False)

    @property
    def canceled_at(self):
        """If the subscription has been canceled, the date of that cancellation."""
        return self.stripe_data.get("canceled_at")

    @property
    def collection_method(self):
        """Either charge_automatically, or send_invoice."""
        return self.stripe_data.get("collection_method", "charge_automatically")

    @property
    def current_period_end(self):
        """End of the current period that the subscription has been invoiced for."""
        return self.stripe_data.get("current_period_end")

    @property
    def current_period_start(self):
        """Start of the current period that the subscription has been invoiced for."""
        return self.stripe_data.get("current_period_start")

    @property
    def days_until_due(self):
        """Number of days a customer has to pay invoices generated by this subscription."""
        return self.stripe_data.get("days_until_due")

    @property
    def default_payment_method(self):
        """ID of the default payment method for the subscription."""
        return self.stripe_data.get("default_payment_method")

    @property
    def default_source(self):
        """ID of the default payment source for the subscription."""
        return self.stripe_data.get("default_source")

    @property
    def default_tax_rates(self):
        """The tax rates that will apply to any subscription item that does not have tax_rates set."""
        return self.stripe_data.get("default_tax_rates", [])

    @property
    def discount(self):
        """Describes the current discount applied to this subscription, if there is one."""
        return self.stripe_data.get("discount")

    @property
    def ended_at(self):
        """If the subscription has ended, the date the subscription ended."""
        return self.stripe_data.get("ended_at")

    @property
    def items(self):
        """List of subscription items, each with an attached price."""
        return self.stripe_data.get("items", {})

    @property
    def latest_invoice(self):
        """The most recent invoice this subscription has generated."""
        return self.stripe_data.get("latest_invoice")

    @property
    def next_pending_invoice_item_invoice(self):
        """Specifies the date on which the next invoice will be generated."""
        return self.stripe_data.get("next_pending_invoice_item_invoice")

    @property
    def pause_collection(self):
        """If specified, payment collection for this subscription will be paused."""
        return self.stripe_data.get("pause_collection")

    @property
    def payment_settings(self):
        """Payment settings passed on to invoices created by the subscription."""
        return self.stripe_data.get("payment_settings", {})

    @property
    def pending_invoice_item_interval(self):
        """Specifies an interval for how often to invoice for any pending invoice items."""
        return self.stripe_data.get("pending_invoice_item_interval")

    @property
    def pending_setup_intent(self):
        """ID of a setup intent for this subscription if one exists."""
        return self.stripe_data.get("pending_setup_intent")

    @property
    def pending_update(self):
        """If specified, pending updates that will be applied to the subscription."""
        return self.stripe_data.get("pending_update")

    @property
    def plan(self):
        """The plan the customer is subscribed to. Only set if single plan."""
        return self.stripe_data.get("plan")

    @property
    def quantity(self):
        """The quantity of the plan to which the customer is subscribed."""
        return self.stripe_data.get("quantity")

    @property
    def schedule(self):
        """The schedule attached to the subscription."""
        return self.stripe_data.get("schedule")

    @property
    def start_date(self):
        """Date when the subscription was created."""
        return self.stripe_data.get("start_date")

    @property
    def status(self):
        """The status of this subscription."""
        return self.stripe_data.get("status")

    @property
    def test_clock(self):
        """ID of the test clock this subscription belongs to."""
        return self.stripe_data.get("test_clock")

    @property
    def transfer_data(self):
        """The account (if any) the subscription's payments will be attributed to."""
        return self.stripe_data.get("transfer_data")

    @property
    def trial_end(self):
        """If the subscription has a trial, the end of that trial."""
        return self.stripe_data.get("trial_end")

    @property
    def trial_start(self):
        """If the subscription has a trial, the beginning of that trial."""
        return self.stripe_data.get("trial_start")

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

        if not kwargs.get("status"):
            # special case: https://stripe.com/docs/api/subscriptions/list#list_subscriptions-status
            # See Issue: https://github.com/dj-stripe/dj-stripe/issues/1763
            kwargs["status"] = "all"
        return super().api_list(api_key=api_key, **kwargs)

    def update(self, plan: Union[StripeModel, str] = None, **kwargs):
        """
        See `Customer.subscribe() <#djstripe.models.Customer.subscribe>`__

        :param plan: The plan to which to subscribe the customer.
        :type plan: Plan or string (plan ID)

        .. important:: Updating a subscription by changing the plan or quantity \
            creates a new ``Subscription`` in \
            Stripe (and dj-stripe).
        """

        # Convert Plan to id
        if plan is not None and isinstance(plan, StripeModel):
            plan = plan.id

        stripe_subscription = self._api_update(plan=plan, **kwargs)

        api_key = kwargs.get("api_key") or self.default_api_key
        return Subscription.sync_from_stripe_data(stripe_subscription, api_key=api_key)

    def extend(self, delta):
        """
        Extends this subscription by the provided delta.

        :param delta: The timedelta by which to extend this subscription.
        :type delta: timedelta
        """

        if delta.total_seconds() < 0:
            raise ValueError("delta must be a positive timedelta.")

        if self.trial_end is not None and self.trial_end > timezone.now():
            period_end = self.trial_end
        else:
            period_end = self.current_period_end

        period_end += delta

        return self.update(proration_behavior="none", trial_end=period_end)

    def cancel(self, at_period_end: bool = False, **kwargs):
        """
        Cancels this subscription. If you set the at_period_end parameter to true,
        the subscription will remain active until the end of the period, at which point
        it will be canceled and not renewed. By default, the subscription is terminated
        immediately. In either case, the customer will not be charged again for
        the subscription. Note, however, that any pending invoice items or metered
        usage will still be charged at the end of the period unless manually
        deleted.

        Depending on how `proration_behavior` is set, any pending prorations will
        also be left in place and collected at the end of the period.
        However, if the subscription is set to cancel immediately, you can pass the
        `prorate` and `invoice_now` flags in `kwargs` to configure how the pending
        metered usage is invoiced and how proration must work.

        By default, all unpaid invoices for the customer will be closed upon
        subscription cancellation. We do this in order to prevent unexpected payment
        retries once the customer has canceled a subscription. However, you can
        reopen the invoices manually after subscription cancellation to have us proceed
        with automatic retries, or you could even re-attempt payment yourself on all
        unpaid invoices before allowing the customer to cancel the
        subscription at all.

        :param at_period_end: A flag that if set to true will delay the cancellation \
            of the subscription until the end of the current period. Default is False.
        :type at_period_end: boolean

        .. important:: If a subscription is canceled during a trial period, \
        the ``at_period_end`` flag will be overridden to False so that the trial ends \
        immediately and the customer's card isn't charged.
        """

        # If plan has trial days and customer cancels before
        # trial period ends, then end subscription now,
        # i.e. at_period_end=False
        if self.trial_end and self.trial_end > timezone.now():
            at_period_end = False

        if at_period_end:
            stripe_subscription = self._api_update(cancel_at_period_end=True, **kwargs)
        else:
            try:
                stripe_subscription = self._api_delete(**kwargs)
            except InvalidRequestError as exc:
                if "No such subscription:" in str(exc):
                    # cancel() works by deleting the subscription. The object still
                    # exists in Stripe however, and can still be retrieved.
                    # If the subscription was already canceled (status=canceled),
                    # that api_retrieve() call will fail with "No such subscription".
                    # However, this may also happen if the subscription legitimately
                    # does not exist, in which case the following line will re-raise.
                    stripe_subscription = self.api_retrieve()
                else:
                    raise

        return Subscription.sync_from_stripe_data(
            stripe_subscription, api_key=self.default_api_key
        )

    def reactivate(self):
        """
        Reactivates this subscription.

        If a customer's subscription is canceled with ``at_period_end`` set to True and
        it has not yet reached the end of the billing period, it can be reactivated.
        Subscriptions canceled immediately cannot be reactivated.
        (Source: https://stripe.com/docs/billing/subscriptions/cancel)

        .. warning:: Reactivating a fully canceled Subscription will fail silently. \
        Be sure to check the returned Subscription's status.
        """
        if not self.plan:
            return None
        stripe_subscription = self.api_retrieve()
        stripe_subscription.plan = self.plan.id
        stripe_subscription.cancel_at_period_end = False

        return Subscription.sync_from_stripe_data(stripe_subscription.save())

    def is_period_current(self):
        """
        Returns True if this subscription's period is current, false otherwise.
        """

        return self.current_period_end > timezone.now() or (
            self.trial_end and self.trial_end > timezone.now()
        )

    def is_status_current(self):
        """
        Returns True if this subscription's status is current (active or trialing),
        false otherwise.
        """

        return self.status in ("trialing", "active")

    def is_status_temporarily_current(self):
        """
        A status is temporarily current when the subscription is canceled with the
        ``at_period_end`` flag.
        The subscription is still active, but is technically canceled and we're just
        waiting for it to run out.

        You could use this method to give customers limited service after they've
        canceled. For example, a video on demand service could only allow customers
        to download their libraries and do nothing else when their
        subscription is temporarily current.
        """

        return (
            self.canceled_at
            and self.cancel_at_period_end
            and timezone.now() < self.current_period_end
        )

    def is_valid(self):
        """
        Returns True if this subscription's status and period are current,
        false otherwise.
        """

        if not self.is_status_current():
            return False

        if not self.is_period_current():
            return False

        return True

    def _attach_objects_post_save_hook(
        self,
        cls,
        data,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
        pending_relations=None,
    ):
        super()._attach_objects_post_save_hook(
            cls, data, api_key=api_key, pending_relations=pending_relations
        )

        cls._stripe_object_to_subscription_items(
            target_cls=SubscriptionItem, data=data, subscription=self, api_key=api_key
        )

        cls._stripe_object_to_default_tax_rates(
            target_cls=TaxRate, data=data, api_key=api_key
        )


class SubscriptionItem(StripeModel):
    """
    Subscription items allow you to create customer subscriptions
    with more than one plan, making it easy to represent complex billing relationships.

    Stripe documentation: https://stripe.com/docs/api?lang=python#subscription_items
    """

    stripe_class = stripe.SubscriptionItem

    # Fields converted to properties - see below
    plan = models.ForeignKey(
        "Plan",
        on_delete=models.CASCADE,
        related_name="subscription_items",
        help_text="The plan the customer is subscribed to.",
    )
    price = models.ForeignKey(
        "Price",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subscription_items",
        help_text="The price the customer is subscribed to.",
    )
    # Other fields converted to properties - see below
    subscription = StripeForeignKey(
        "Subscription",
        on_delete=models.CASCADE,
        related_name="items",
        help_text="The subscription this subscription item belongs to.",
    )
    tax_rates = models.ManyToManyField(
        "TaxRate",
        # explicitly specify the joining table name as though the joining model
        # was defined with through="DjstripeSubscriptionItemTaxRate"
        db_table="djstripe_djstripesubscriptionitemtaxrate",
        related_name="+",
        blank=True,
        help_text=(
            "The tax rates which apply to this subscription_item. When set, "
            "the default_tax_rates on the subscription do not apply to this "
            "subscription_item."
        ),
    )

    # Properties replacing field definitions
    @property
    def billing_thresholds(self):
        """Define thresholds at which an invoice will be sent, and the related subscription advanced to a new billing period."""
        return self.stripe_data.get("billing_thresholds")

    @property
    def proration_behavior(self):
        """Determines how to handle prorations when the billing cycle changes."""
        return self.stripe_data.get("proration_behavior", "create_prorations")

    @property
    def proration_date(self):
        """If set, the proration will be calculated as though the subscription was updated at the given time."""
        return self.stripe_data.get("proration_date")

    @property
    def quantity(self):
        """The quantity of the plan to which the customer should be subscribed."""
        return self.stripe_data.get("quantity")

    def _attach_objects_post_save_hook(
        self,
        cls,
        data,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
        pending_relations=None,
    ):
        super()._attach_objects_post_save_hook(
            cls, data, api_key=api_key, pending_relations=pending_relations
        )

        self.tax_rates.set(
            cls._stripe_object_to_tax_rates(
                target_cls=TaxRate, data=data, api_key=api_key
            )
        )


class SubscriptionSchedule(StripeModel):
    """
    Subscription schedules allow you to create and manage the lifecycle
    of a subscription by predefining expected changes.

    Stripe documentation: https://stripe.com/docs/api/subscription_schedules?lang=python
    """

    stripe_class = stripe.SubscriptionSchedule
    stripe_dashboard_item_name = "subscription_schedules"

    canceled_at = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="Time at which the subscription schedule was canceled.",
    )
    completed_at = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="Time at which the subscription schedule was completed.",
    )
    current_phase = JSONField(
        null=True,
        blank=True,
        help_text=(
            "Object representing the start and end dates for the "
            "current phase of the subscription schedule, if it is `active`."
        ),
    )
    customer = models.ForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        related_name="schedules",
        help_text="The customer who owns the subscription schedule.",
    )
    default_settings = JSONField(
        null=True,
        blank=True,
        help_text="Object representing the subscription schedule's default settings.",
    )
    end_behavior = StripeEnumField(
        enum=enums.SubscriptionScheduleEndBehavior,
        help_text=(
            "Behavior of the subscription schedule and underlying "
            "subscription when it ends."
        ),
    )
    phases = JSONField(
        null=True,
        blank=True,
        help_text="Configuration for the subscription schedule's phases.",
    )
    released_at = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="Time at which the subscription schedule was released.",
    )
    released_subscription = models.ForeignKey(
        "Subscription",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="released_schedules",
        help_text=(
            "The subscription once managed by this subscription schedule "
            "(if it is released)."
        ),
    )
    status = StripeEnumField(
        enum=enums.SubscriptionScheduleStatus,
        help_text=(
            "The present status of the subscription schedule. Possible "
            "values are `not_started`, `active`, `completed`, `released`, and "
            "`canceled`."
        ),
    )
    subscription = models.ForeignKey(
        "Subscription",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subscriptions",
        help_text="ID of the subscription managed by the subscription schedule.",
    )

    def release(self, api_key=None, stripe_account=None, **kwargs):
        """
        Releases the subscription schedule immediately, which will stop scheduling
        of its phases, but leave any existing subscription in place.
        A schedule can only be released if its status is not_started or active.
        If the subscription schedule is currently associated with a subscription,
        releasing it will remove its subscription property and set the subscription’s
        ID to the released_subscription property
        and returns the Released SubscriptionSchedule.
        :param api_key: The api key to use for this request.
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        """

        api_key = api_key or self.default_api_key

        # Prefer passed in stripe_account if set.
        if not stripe_account:
            stripe_account = self._get_stripe_account_id(api_key)

        stripe_subscription_schedule = self.stripe_class.release(
            self.id,
            api_key=api_key,
            stripe_account=stripe_account,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
            **kwargs,
        )

        return SubscriptionSchedule.sync_from_stripe_data(stripe_subscription_schedule)

    def cancel(self, api_key=None, stripe_account=None, **kwargs):
        """
        Cancels a subscription schedule and its associated subscription immediately
        (if the subscription schedule has an active subscription). A subscription schedule can only be canceled if its status is not_started or active
        and returns the Canceled SubscriptionSchedule.
        :param api_key: The api key to use for this request.
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        """

        api_key = api_key or self.default_api_key

        # Prefer passed in stripe_account if set.
        if not stripe_account:
            stripe_account = self._get_stripe_account_id(api_key)

        stripe_subscription_schedule = self.stripe_class.cancel(
            self.id,
            api_key=api_key,
            stripe_account=stripe_account,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
            **kwargs,
        )

        return SubscriptionSchedule.sync_from_stripe_data(stripe_subscription_schedule)

    def update(self, api_key=None, stripe_account=None, **kwargs):
        """
        Updates an existing subscription schedule
        and returns the updated SubscriptionSchedule.
        :param api_key: The api key to use for this request.
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        """
        stripe_subscription_schedule = self._api_update(
            api_key=api_key, stripe_account=stripe_account, **kwargs
        )
        return SubscriptionSchedule.sync_from_stripe_data(stripe_subscription_schedule)


class ShippingRate(StripeModel):
    """
    Shipping rates describe the price of shipping presented
    to your customers and can be applied to Checkout Sessions
    to collect shipping costs.

    Stripe documentation: https://stripe.com/docs/api/shipping_rates
    """

    stripe_class = stripe.ShippingRate
    stripe_dashboard_item_name = "shipping-rates"
    description = None

    # Foreign key remains as model field
    tax_code = StripeForeignKey(
        "TaxCode",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="The shipping tax code",
    )

    # Properties replacing field definitions
    @property
    def active(self):
        """Whether the shipping rate can be used for new purchases. Defaults to true."""
        return self.stripe_data.get("active", True)

    @property
    def display_name(self):
        """The name of the shipping rate, meant to be displayable to the customer. This will appear on CheckoutSessions."""
        return self.stripe_data.get("display_name", "")

    @property
    def fixed_amount(self):
        """Describes a fixed amount to charge for shipping. Must be present if type is fixed_amount."""
        return self.stripe_data.get("fixed_amount", {})

    @property
    def type(self):
        """The type of calculation to use on the shipping rate. Can only be fixed_amount for now."""
        return self.stripe_data.get("type", "fixed_amount")

    @property
    def delivery_estimate(self):
        """The estimated range for how long shipping will take, meant to be displayable to the customer. This will appear on CheckoutSessions."""
        return self.stripe_data.get("delivery_estimate")

    @property
    def tax_behavior(self):
        """Specifies whether the rate is considered inclusive of taxes or exclusive of taxes."""
        return self.stripe_data.get("tax_behavior")

    class Meta(StripeModel.Meta):
        verbose_name = "Shipping Rate"

    def __str__(self):
        fixed_amount = self.fixed_amount or {}
        amount_value = fixed_amount.get("amount")
        currency = fixed_amount.get("currency")

        if amount_value is not None and currency:
            amount = get_friendly_currency_amount(amount_value / 100, currency)
        else:
            amount = "N/A"

        if self.active:
            return f"{self.display_name} - {amount} (Active)"
        return f"{self.display_name} - {amount} (Archived)"


class TaxCode(StripeModel):
    """
    Tax codes classify goods and services for tax purposes.

    Stripe documentation: https://stripe.com/docs/api/tax_codes
    """

    stripe_class = stripe.TaxCode
    metadata = None

    # Properties replacing field definitions
    @property
    def name(self):
        """A short name for the tax code."""
        return self.stripe_data.get("name", "")

    class Meta(StripeModel.Meta):
        verbose_name = "Tax Code"

    def __str__(self):
        return f"{self.name}: {self.id}"

    @classmethod
    def _find_owner_account(cls, data, api_key=djstripe_settings.STRIPE_SECRET_KEY):
        # Tax Codes do not belong to any Stripe Account
        pass


class TaxId(StripeModel):
    """
    Add one or multiple tax IDs to a customer.
    A customer's tax IDs are displayed on invoices and
    credit notes issued for the customer.

    Stripe documentation: https://stripe.com/docs/api/customer_tax_ids?lang=python
    """

    stripe_class = stripe.TaxId
    description = None
    metadata = None

    # Foreign key remains as model field
    customer = StripeForeignKey(
        "djstripe.customer",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tax_ids",
    )

    # Properties replacing field definitions
    @property
    def country(self):
        """Two-letter ISO code representing the country of the tax ID."""
        return self.stripe_data.get("country", "")

    @property
    def type(self):
        """The type of tax ID."""
        return self.stripe_data.get("type")

    @property
    def value(self):
        """Value of the tax ID."""
        return self.stripe_data.get("value", "")

    def __str__(self):
        return f"{enums.TaxIdType.humanize(self.type)} {self.value}"

    class Meta(StripeModel.Meta):
        verbose_name = "Tax ID"

    @property
    def verification(self) -> dict | None:
        return self.stripe_data.get("verification", None)


class TaxRate(StripeModel):
    """
    Tax rates can be applied to invoices and subscriptions to collect tax.

    Stripe documentation: https://stripe.com/docs/api/tax_rates?lang=python
    """

    stripe_class = stripe.TaxRate
    stripe_dashboard_item_name = "tax-rates"

    # Properties replacing field definitions
    @property
    def active(self):
        """Defaults to true. When set to false, this tax rate cannot be applied to objects in the API, but will still be applied to subscriptions and invoices that already have it set."""
        return self.stripe_data.get("active", True)

    @property
    def country(self):
        """Two-letter country code."""
        return self.stripe_data.get("country", "")

    @property
    def display_name(self):
        """The display name of the tax rates as it will appear to your customer on their receipt email, PDF, and the hosted invoice page."""
        return self.stripe_data.get("display_name", "")

    @property
    def inclusive(self):
        """This specifies if the tax rate is inclusive or exclusive."""
        return self.stripe_data.get("inclusive", False)

    @property
    def jurisdiction(self):
        """The jurisdiction for the tax rate."""
        return self.stripe_data.get("jurisdiction", "")

    @property
    def percentage(self):
        """This represents the tax rate percent out of 100."""
        return self.stripe_data.get("percentage", 0.0)

    @property
    def state(self):
        """ISO 3166-2 subdivision code, without country prefix."""
        return self.stripe_data.get("state", "")

    @property
    def tax_type(self):
        """The high-level tax type, such as vat, gst, sales_tax or custom."""
        return self.stripe_data.get("tax_type", "")

    def __str__(self):
        return f"{self.display_name} at {self.percentage}%"

    class Meta(StripeModel.Meta):
        verbose_name = "Tax Rate"
