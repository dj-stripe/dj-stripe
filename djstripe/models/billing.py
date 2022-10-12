import warnings
from typing import Optional, Union

import stripe
from django.db import models
from django.utils import timezone
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from stripe.error import InvalidRequestError

from .. import enums
from ..fields import (
    JSONField,
    PaymentMethodForeignKey,
    StripeCurrencyCodeField,
    StripeDateTimeField,
    StripeDecimalCurrencyAmountField,
    StripeEnumField,
    StripeForeignKey,
    StripeIdField,
    StripePercentField,
    StripeQuantumCurrencyAmountField,
)
from ..managers import SubscriptionManager
from ..settings import djstripe_settings
from ..utils import QuerySetMock, get_friendly_currency_amount
from .base import StripeModel
from .core import Customer


# TODO Mimic stripe-python decorator pattern to easily add and expose CRUD operations like create, update, delete etc on models
# TODO Add Tests
class DjstripeInvoiceTotalTaxAmount(models.Model):
    """
    An internal model that holds the value of elements of Invoice.total_tax_amounts

    Note that this is named with the prefix Djstripe to avoid potential
    collision with a Stripe API object name.
    """

    invoice = StripeForeignKey(
        "Invoice", on_delete=models.CASCADE, related_name="total_tax_amounts"
    )

    amount = StripeQuantumCurrencyAmountField(
        help_text="The amount, in cents, of the tax."
    )
    inclusive = models.BooleanField(
        help_text="Whether this tax amount is inclusive or exclusive."
    )
    tax_rate = StripeForeignKey(
        "TaxRate",
        on_delete=models.CASCADE,
        help_text="The tax rate that was applied to get this tax amount.",
    )

    class Meta:
        unique_together = ["invoice", "tax_rate"]


# TODO Add Tests
class DjstripeUpcomingInvoiceTotalTaxAmount(models.Model):
    """
    As per DjstripeInvoiceTotalTaxAmount, except for UpcomingInvoice
    """

    invoice = models.ForeignKey(
        # Don't define related_name since property is defined in UpcomingInvoice
        "UpcomingInvoice",
        on_delete=models.CASCADE,
        related_name="+",
    )

    amount = StripeQuantumCurrencyAmountField(
        help_text="The amount, in cents, of the tax."
    )
    inclusive = models.BooleanField(
        help_text="Whether this tax amount is inclusive or exclusive."
    )
    tax_rate = StripeForeignKey(
        "TaxRate",
        on_delete=models.CASCADE,
        help_text="The tax rate that was applied to get this tax amount.",
    )

    class Meta:
        unique_together = ["invoice", "tax_rate"]


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

    id = StripeIdField(max_length=500)
    applies_to = JSONField(
        null=True,
        blank=True,
        help_text="Contains information about what this coupon applies to.",
    )
    amount_off = StripeDecimalCurrencyAmountField(
        null=True,
        blank=True,
        help_text="Amount (as decimal) that will be taken off the subtotal of any "
        "invoices for this customer.",
    )
    currency = StripeCurrencyCodeField(null=True, blank=True)
    duration = StripeEnumField(
        enum=enums.CouponDuration,
        help_text=(
            "Describes how long a customer who applies this coupon "
            "will get the discount."
        ),
        default=enums.CouponDuration.once,
    )
    duration_in_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="If `duration` is `repeating`, the number of months "
        "the coupon applies.",
    )
    max_redemptions = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of times this coupon can be redeemed, in total, "
        "before it is no longer valid.",
    )
    name = models.TextField(
        max_length=5000,
        default="",
        blank=True,
        help_text=(
            "Name of the coupon displayed to customers on for instance invoices "
            "or receipts."
        ),
    )
    percent_off = StripePercentField(
        null=True,
        blank=True,
        help_text=(
            "Percent that will be taken off the subtotal of any invoices for "
            "this customer for the duration of the coupon. "
            "For example, a coupon with percent_off of 50 will make a "
            "$100 invoice $50 instead."
        ),
    )
    redeem_by = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="Date after which the coupon can no longer be redeemed. "
        "Max 5 years in the future.",
    )
    times_redeemed = models.PositiveIntegerField(
        editable=False,
        default=0,
        help_text="Number of times this coupon has been applied to a customer.",
    )
    # valid = models.BooleanField(editable=False)

    class Meta(StripeModel.Meta):
        unique_together = ("id", "livemode")

    def __str__(self):
        if self.name:
            return self.name
        return self.human_readable

    @property
    def human_readable_amount(self):
        if self.percent_off:
            amount = f"{self.percent_off}%"
        elif self.currency:
            amount = get_friendly_currency_amount(self.amount_off or 0, self.currency)
        else:
            amount = "(invalid amount)"
        return f"{amount} off"

    @property
    def human_readable(self):
        if self.duration == enums.CouponDuration.repeating:
            if self.duration_in_months == 1:
                duration = "for {duration_in_months} month"
            else:
                duration = "for {duration_in_months} months"
            duration = duration.format(duration_in_months=self.duration_in_months)
        else:
            duration = self.duration
        return f"{self.human_readable_amount} {duration}"


class BaseInvoice(StripeModel):
    """
    The abstract base model shared by Invoice and UpcomingInvoice

    Note:
    Most fields are defined on BaseInvoice so they're available to both models.
    ManyToManyFields are an exception, since UpcomingInvoice doesn't exist in the db.
    """

    stripe_class = stripe.Invoice
    stripe_dashboard_item_name = "invoices"

    account_country = models.CharField(
        max_length=2,
        default="",
        blank=True,
        help_text="The country of the business associated with this invoice, "
        "most often the business creating the invoice.",
    )
    account_name = models.TextField(
        max_length=5000,
        blank=True,
        help_text="The public name of the business associated with this invoice, "
        "most often the business creating the invoice.",
    )
    amount_due = StripeDecimalCurrencyAmountField(
        help_text="Final amount due (as decimal) at this time for this invoice. "
        "If the invoice's total is smaller than the minimum charge amount, "
        "for example, or if there is account credit that can be applied to the "
        "invoice, the amount_due may be 0. If there is a positive starting_balance "
        "for the invoice (the customer owes money), the amount_due will also take that "
        "into account. The charge that gets generated for the invoice will be for "
        "the amount specified in amount_due."
    )
    amount_paid = StripeDecimalCurrencyAmountField(
        null=True,  # XXX: This is not nullable, but it's a new field
        help_text="The amount, (as decimal), that was paid.",
    )
    amount_remaining = StripeDecimalCurrencyAmountField(
        null=True,  # XXX: This is not nullable, but it's a new field
        help_text="The amount remaining, (as decimal), that is due.",
    )
    application_fee_amount = StripeDecimalCurrencyAmountField(
        null=True,
        blank=True,
        help_text="The fee (as decimal) that will be applied to the invoice and "
        "transferred to the application owner's "
        "Stripe account when the invoice is paid.",
    )
    attempt_count = models.IntegerField(
        help_text="Number of payment attempts made for this invoice, "
        "from the perspective of the payment retry schedule. "
        "Any payment attempt counts as the first attempt, and subsequently "
        "only automatic retries increment the attempt count. "
        "In other words, manual payment attempts after the first attempt do not affect "
        "the retry schedule."
    )
    attempted = models.BooleanField(
        default=False,
        help_text="Whether or not an attempt has been made to pay the invoice. "
        "An invoice is not attempted until 1 hour after the ``invoice.created`` "
        "webhook, for example, so you might not want to display that invoice as "
        "unpaid to your users.",
    )
    auto_advance = models.BooleanField(
        null=True,
        help_text="Controls whether Stripe will perform automatic collection of the "
        "invoice. When false, the invoice's state will not automatically "
        "advance without an explicit action.",
    )
    billing_reason = StripeEnumField(
        default="",
        blank=True,
        enum=enums.InvoiceBillingReason,
        help_text="Indicates the reason why the invoice was created. "
        "subscription_cycle indicates an invoice created by a subscription advancing "
        "into a new period. subscription_create indicates an invoice created due to "
        "creating a subscription. subscription_update indicates an invoice created due "
        "to updating a subscription. subscription is set for all old invoices to "
        "indicate either a change to a subscription or a period advancement. "
        "manual is set for all invoices unrelated to a subscription "
        "(for example: created via the invoice editor). The upcoming value is "
        "reserved for simulated invoices per the upcoming invoice endpoint. "
        "subscription_threshold indicates an invoice created due to a billing "
        "threshold being reached.",
    )
    charge = models.OneToOneField(
        "Charge",
        on_delete=models.CASCADE,
        null=True,
        # we need to use the %(class)s placeholder to avoid related name
        # clashes between Invoice and UpcomingInvoice
        related_name="latest_%(class)s",
        help_text="The latest charge generated for this invoice, if any.",
    )
    collection_method = StripeEnumField(
        enum=enums.InvoiceCollectionMethod,
        null=True,
        help_text=(
            "When charging automatically, Stripe will attempt to pay this invoice "
            "using the default source attached to the customer. "
            "When sending an invoice, Stripe will email this invoice to the customer "
            "with payment instructions."
        ),
    )
    currency = StripeCurrencyCodeField()
    customer = StripeForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        # we need to use the %(class)s placeholder to avoid related name
        # clashes between Invoice and UpcomingInvoice
        related_name="%(class)ss",
        help_text="The customer associated with this invoice.",
    )
    customer_address = JSONField(
        null=True,
        blank=True,
        help_text="The customer's address. Until the invoice is finalized, this "
        "field will equal customer.address. Once the invoice is finalized, this field "
        "will no longer be updated.",
    )
    customer_email = models.TextField(
        max_length=5000,
        blank=True,
        help_text="The customer's email. Until the invoice is finalized, this field "
        "will equal customer.email. Once the invoice is finalized, this field will no "
        "longer be updated.",
    )
    customer_name = models.TextField(
        max_length=5000,
        blank=True,
        help_text="The customer's name. Until the invoice is finalized, this field "
        "will equal customer.name. Once the invoice is finalized, this field will no "
        "longer be updated.",
    )
    customer_phone = models.TextField(
        max_length=5000,
        blank=True,
        help_text="The customer's phone number. Until the invoice is finalized, "
        "this field will equal customer.phone. Once the invoice is finalized, "
        "this field will no longer be updated.",
    )
    customer_shipping = JSONField(
        null=True,
        blank=True,
        help_text="The customer's shipping information. Until the invoice is "
        "finalized, this field will equal customer.shipping. Once the invoice is "
        "finalized, this field will no longer be updated.",
    )
    customer_tax_exempt = StripeEnumField(
        enum=enums.CustomerTaxExempt,
        default="",
        help_text="The customer's tax exempt status. Until the invoice is finalized, "
        "this field will equal customer.tax_exempt. Once the invoice is "
        "finalized, this field will no longer be updated.",
    )
    default_payment_method = StripeForeignKey(
        "PaymentMethod",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Default payment method for the invoice. It must belong to the "
        "customer associated with the invoice. If not set, defaults to the "
        "subscription's default payment method, if any, or to the default payment "
        "method in the customer's invoice settings.",
    )
    # Note: default_tax_rates is handled in the subclasses since it's a
    # ManyToManyField, otherwise reverse accessors clash
    discount = JSONField(
        null=True,
        blank=True,
        help_text="Describes the current discount applied to this "
        "subscription, if there is one. When billing, a discount applied to a "
        "subscription overrides a discount applied on a customer-wide basis.",
    )
    due_date = StripeDateTimeField(
        null=True,
        blank=True,
        help_text=(
            "The date on which payment for this invoice is due. "
            "This value will be null for invoices where billing=charge_automatically."
        ),
    )
    ending_balance = StripeQuantumCurrencyAmountField(
        null=True,
        help_text="Ending customer balance (in cents) after attempting to pay invoice. "
        "If the invoice has not been attempted yet, this will be null.",
    )
    footer = models.TextField(
        max_length=5000, blank=True, help_text="Footer displayed on the invoice."
    )
    hosted_invoice_url = models.TextField(
        max_length=799,
        default="",
        blank=True,
        help_text="The URL for the hosted invoice page, which allows customers to view "
        "and pay an invoice. If the invoice has not been frozen yet, "
        "this will be null.",
    )
    invoice_pdf = models.TextField(
        max_length=799,
        default="",
        blank=True,
        help_text=(
            "The link to download the PDF for the invoice. "
            "If the invoice has not been frozen yet, this will be null."
        ),
    )
    # TODO: Implement "lines" (InvoiceLineItem related_field)
    next_payment_attempt = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="The time at which payment will next be attempted.",
    )
    number = models.CharField(
        max_length=64,
        default="",
        blank=True,
        help_text=(
            "A unique, identifying string that appears on emails sent to the customer "
            "for this invoice. "
            "This starts with the customer's unique invoice_prefix if it is specified."
        ),
    )
    paid = models.BooleanField(
        default=False,
        help_text=(
            "Whether payment was successfully collected for this invoice. An invoice "
            "can be paid (most commonly) with a charge or with credit from the "
            "customer's account balance."
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
    period_end = StripeDateTimeField(
        help_text="End of the usage period during which invoice items were "
        "added to this invoice."
    )
    period_start = StripeDateTimeField(
        help_text="Start of the usage period during which invoice items were "
        "added to this invoice."
    )
    post_payment_credit_notes_amount = StripeQuantumCurrencyAmountField(
        # This is not nullable, but it's a new field
        null=True,
        blank=True,
        help_text="Total amount (in cents) of all post-payment credit notes issued "
        "for this invoice.",
    )
    pre_payment_credit_notes_amount = StripeQuantumCurrencyAmountField(
        # This is not nullable, but it's a new field
        null=True,
        blank=True,
        help_text="Total amount (in cents) of all pre-payment credit notes issued "
        "for this invoice.",
    )
    receipt_number = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text=(
            "This is the transaction number that appears on email receipts "
            "sent for this invoice."
        ),
    )
    starting_balance = StripeQuantumCurrencyAmountField(
        help_text="Starting customer balance (in cents) before attempting to pay "
        "invoice. If the invoice has not been attempted yet, this will be the "
        "current customer balance."
    )
    statement_descriptor = models.CharField(
        max_length=22,
        default="",
        blank=True,
        help_text="An arbitrary string to be displayed on your customer's "
        "credit card statement. The statement description may not include <>\"' "
        "characters, and will appear on your customer's statement in capital letters. "
        "Non-ASCII characters are automatically stripped. "
        "While most banks display this information consistently, "
        "some may display it incorrectly or not at all.",
    )
    status = StripeEnumField(
        default="",
        blank=True,
        enum=enums.InvoiceStatus,
        help_text="The status of the invoice, one of draft, open, paid, "
        "uncollectible, or void.",
    )
    status_transitions = JSONField(null=True, blank=True)
    subscription = StripeForeignKey(
        "Subscription",
        null=True,
        # we need to use the %(class)s placeholder to avoid related name
        # clashes between Invoice and UpcomingInvoice
        related_name="%(class)ss",
        on_delete=models.SET_NULL,
        help_text="The subscription that this invoice was prepared for, if any.",
    )
    subscription_proration_date = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="Only set for upcoming invoices that preview prorations. "
        "The time used to calculate prorations.",
    )
    subtotal = StripeDecimalCurrencyAmountField(
        help_text="Total (as decimal) of all subscriptions, invoice items, "
        "and prorations on the invoice before any discount or tax is applied."
    )
    tax = StripeDecimalCurrencyAmountField(
        null=True,
        blank=True,
        help_text="The amount (as decimal) of tax included in the total, calculated "
        "from ``tax_percent`` and the subtotal. If no "
        "``tax_percent`` is defined, this value will be null.",
    )
    tax_percent = StripePercentField(
        null=True,
        blank=True,
        help_text="This percentage of the subtotal has been added to the total amount "
        "of the invoice, including invoice line items and discounts. "
        "This field is inherited from the subscription's ``tax_percent`` field, "
        "but can be changed before the invoice is paid. This field defaults to null.",
    )
    threshold_reason = JSONField(
        null=True,
        blank=True,
        help_text="If billing_reason is set to subscription_threshold this returns "
        "more information on which threshold rules triggered the invoice.",
    )
    total = StripeDecimalCurrencyAmountField("Total (as decimal) after discount.")
    webhooks_delivered_at = StripeDateTimeField(
        null=True,
        help_text=(
            "The time at which webhooks for this invoice were successfully delivered "
            "(if the invoice had no webhooks to deliver, this will match `date`). "
            "Invoice payment is delayed until webhooks are delivered, or until all "
            "webhook delivery attempts have been exhausted."
        ),
    )

    class Meta(StripeModel.Meta):
        abstract = True
        ordering = ["-created"]

    def __str__(self):
        invoice_number = self.number or self.receipt_number or self.id
        amount = get_friendly_currency_amount(self.amount_paid or 0, self.currency)
        return f"Invoice #{invoice_number} for {amount} ({self.status})"

    @classmethod
    def upcoming(
        cls,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
        customer=None,
        coupon=None,
        subscription=None,
        subscription_plan=None,
        subscription_prorate=None,
        subscription_proration_date=None,
        subscription_quantity=None,
        subscription_trial_end=None,
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
        :param subscription_prorate: If previewing an update to a subscription, \
        this decides whether the preview will show the result of applying \
        prorations or not.
        :type subscription_prorate: bool
        :param subscription_proration_date: If previewing an update to a \
        subscription, and doing proration, subscription_proration_date forces \
        the proration to be calculated as though the update was done at the \
        specified time.
        :type subscription_proration_date: datetime
        :param subscription_quantity: If provided, the invoice returned will \
        preview updating or creating a subscription with that quantity.
        :type subscription_quantity: int
        :param subscription_trial_end: If provided, the invoice returned will \
        preview updating or creating a subscription with that trial end.
        :type subscription_trial_end: datetime
        :returns: The upcoming preview invoice.
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
                coupon=coupon,
                subscription=subscription,
                subscription_plan=subscription_plan,
                subscription_prorate=subscription_prorate,
                subscription_proration_date=subscription_proration_date,
                subscription_quantity=subscription_quantity,
                subscription_trial_end=subscription_trial_end,
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

    def retry(self):
        """Retry payment on this invoice if it isn't paid or uncollectible."""

        if (
            self.status != enums.InvoiceStatus.paid
            and self.status != enums.InvoiceStatus.uncollectible
            and self.auto_advance
        ):
            stripe_invoice = self.api_retrieve()
            updated_stripe_invoice = (
                stripe_invoice.pay()
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

        # InvoiceItems need a saved invoice because they're associated via a
        # RelatedManager, so this must be done as part of the post save hook.
        cls._stripe_object_to_invoice_items(
            target_cls=InvoiceItem, data=data, invoice=self, api_key=api_key
        )

    @property
    def plan(self) -> Optional["Plan"]:
        """Gets the associated plan for this invoice.

        In order to provide a consistent view of invoices, the plan object
        should be taken from the first invoice item that has one, rather than
        using the plan associated with the subscription.

        Subscriptions (and their associated plan) are updated by the customer
        and represent what is current, but invoice items are immutable within
        the invoice and stay static/unchanged.

        In other words, a plan retrieved from an invoice item will represent
        the plan as it was at the time an invoice was issued.  The plan
        retrieved from the subscription will be the currently active plan.

        :returns: The associated plan for the invoice.
        """

        for invoiceitem in self.invoiceitems.all():
            if invoiceitem.plan:
                return invoiceitem.plan

        if self.subscription:
            return self.subscription.plan

        return None


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

    default_source = PaymentMethodForeignKey(
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
        help_text="The default payment source for the invoice. "
        "It must belong to the customer associated with the invoice and be "
        "in a chargeable state. If not set, defaults to the subscription's "
        "default source, if any, or to the customer's default source.",
    )

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

        self.default_tax_rates.set(
            cls._stripe_object_to_default_tax_rates(
                target_cls=TaxRate, data=data, api_key=api_key
            )
        )

        cls._stripe_object_set_total_tax_amounts(
            target_cls=DjstripeInvoiceTotalTaxAmount,
            data=data,
            instance=self,
            api_key=api_key,
        )


class UpcomingInvoice(BaseInvoice):
    """
    The preview of an upcoming invoice - does not exist in the Django database.

    See BaseInvoice.upcoming()

    Logically it should be set abstract, but that doesn't quite work since we
    do actually want to instantiate the model and use relations.
    """

    default_source = PaymentMethodForeignKey(
        on_delete=models.SET_NULL,
        null=True,
        related_name="upcoming_invoices",
        help_text="The default payment source for the invoice. "
        "It must belong to the customer associated with the invoice and be "
        "in a chargeable state. If not set, defaults to the subscription's "
        "default source, if any, or to the customer's default source.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._invoiceitems = []
        self._default_tax_rates = []
        self._total_tax_amounts = []

    def get_stripe_dashboard_url(self):
        return ""

    def _attach_objects_hook(
        self, cls, data, api_key=djstripe_settings.STRIPE_SECRET_KEY, current_ids=None
    ):
        super()._attach_objects_hook(
            cls, data, api_key=api_key, current_ids=current_ids
        )
        self._invoiceitems = cls._stripe_object_to_invoice_items(
            target_cls=InvoiceItem, data=data, invoice=self, api_key=api_key
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

        total_tax_amounts = []

        for tax_amount_data in data.get("total_tax_amounts", []):
            tax_rate_id = tax_amount_data["tax_rate"]
            if not isinstance(tax_rate_id, str):
                tax_rate_id = tax_rate_id["tax_rate"]

            tax_rate = TaxRate._get_or_retrieve(id=tax_rate_id, api_key=api_key)

            tax_amount = DjstripeUpcomingInvoiceTotalTaxAmount(
                invoice=self,
                amount=tax_amount_data["amount"],
                inclusive=tax_amount_data["inclusive"],
                tax_rate=tax_rate,
            )

            total_tax_amounts.append(tax_amount)

        self._total_tax_amounts = total_tax_amounts

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

        return QuerySetMock.from_iterable(InvoiceItem, self._invoiceitems)

    @property
    def default_tax_rates(self):
        """
        Gets the default tax rates associated with this upcoming invoice.
        :return:
        """
        return QuerySetMock.from_iterable(TaxRate, self._default_tax_rates)

    @property
    def total_tax_amounts(self):
        """
        Gets the total tax amounts associated with this upcoming invoice.
        :return:
        """
        return QuerySetMock.from_iterable(
            DjstripeUpcomingInvoiceTotalTaxAmount, self._total_tax_amounts
        )

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

    amount = StripeDecimalCurrencyAmountField(help_text="Amount invoiced (as decimal).")
    currency = StripeCurrencyCodeField()
    customer = StripeForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        related_name="invoiceitems",
        help_text="The customer associated with this invoiceitem.",
    )
    date = StripeDateTimeField(help_text="The date on the invoiceitem.")
    discountable = models.BooleanField(
        default=False,
        help_text="If True, discounts will apply to this invoice item. "
        "Always False for prorations.",
    )
    # TODO: discounts
    invoice = StripeForeignKey(
        "Invoice",
        on_delete=models.CASCADE,
        null=True,
        related_name="invoiceitems",
        help_text="The invoice to which this invoiceitem is attached.",
    )
    period = JSONField()
    period_end = StripeDateTimeField(
        help_text="Might be the date when this invoiceitem's invoice was sent."
    )
    period_start = StripeDateTimeField(
        help_text="Might be the date when this invoiceitem was added to the invoice"
    )
    plan = models.ForeignKey(
        "Plan",
        null=True,
        on_delete=models.SET_NULL,
        help_text="If the invoice item is a proration, the plan of the subscription "
        "for which the proration was computed.",
    )
    price = models.ForeignKey(
        "Price",
        null=True,
        related_name="invoiceitems",
        on_delete=models.SET_NULL,
        help_text="If the invoice item is a proration, the price of the subscription "
        "for which the proration was computed.",
    )
    proration = models.BooleanField(
        default=False,
        help_text="Whether or not the invoice item was created automatically as a "
        "proration adjustment when the customer switched plans.",
    )
    quantity = models.IntegerField(
        null=True,
        blank=True,
        help_text="If the invoice item is a proration, the quantity of the "
        "subscription for which the proration was computed.",
    )
    subscription = StripeForeignKey(
        "Subscription",
        null=True,
        related_name="invoiceitems",
        on_delete=models.SET_NULL,
        help_text="The subscription that this invoice item has been created for, "
        "if any.",
    )
    # XXX: subscription_item
    tax_rates = models.ManyToManyField(
        "TaxRate",
        # explicitly specify the joining table name as though the joining model
        # was defined with through="DjstripeInvoiceItemTaxRate"
        db_table="djstripe_djstripeinvoiceitemtaxrate",
        related_name="+",
        blank=True,
        help_text="The tax rates which apply to this invoice item. When set, "
        "the default_tax_rates on the invoice do not apply to this "
        "invoice item.",
    )
    unit_amount = StripeQuantumCurrencyAmountField(
        null=True,
        blank=True,
        help_text="Unit amount (in the `currency` specified) of the invoice item.",
    )
    unit_amount_decimal = StripeDecimalCurrencyAmountField(
        null=True,
        blank=True,
        max_digits=19,
        decimal_places=12,
        help_text=(
            "Same as `unit_amount`, but contains a decimal value with "
            "at most 12 decimal places."
        ),
    )

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

    def __str__(self):
        return self.description

    @classmethod
    def is_valid_object(cls, data):
        return data and data.get("object") in ("invoiceitem", "line_item")

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

    active = models.BooleanField(
        help_text="Whether the plan can be used for new purchases."
    )
    aggregate_usage = StripeEnumField(
        enum=enums.PlanAggregateUsage,
        default="",
        blank=True,
        help_text=(
            "Specifies a usage aggregation strategy for plans of usage_type=metered. "
            "Allowed values are `sum` for summing up all usage during a period, "
            "`last_during_period` for picking the last usage record reported within a "
            "period, `last_ever` for picking the last usage record ever (across period "
            "bounds) or max which picks the usage record with the maximum reported "
            "usage during a period. Defaults to `sum`."
        ),
    )
    amount = StripeDecimalCurrencyAmountField(
        null=True,
        blank=True,
        help_text="Amount (as decimal) to be charged on the interval specified.",
    )
    amount_decimal = StripeDecimalCurrencyAmountField(
        null=True,
        blank=True,
        max_digits=19,
        decimal_places=12,
        help_text=(
            "The unit amount in cents to be charged, represented as a decimal "
            "string with at most 12 decimal places."
        ),
    )
    billing_scheme = StripeEnumField(
        enum=enums.BillingScheme,
        default="",
        blank=True,
        help_text=(
            "Describes how to compute the price per period. "
            "Either `per_unit` or `tiered`. "
            "`per_unit` indicates that the fixed amount (specified in amount) "
            "will be charged per unit in quantity "
            "(for plans with `usage_type=licensed`), or per unit of total "
            "usage (for plans with `usage_type=metered`). "
            "`tiered` indicates that the unit pricing will be computed using "
            "a tiering strategy as defined using the tiers and tiers_mode attributes."
        ),
    )
    currency = StripeCurrencyCodeField()
    interval = StripeEnumField(
        enum=enums.PlanInterval,
        help_text="The frequency with which a subscription should be billed.",
    )
    interval_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "The number of intervals (specified in the interval property) "
            "between each subscription billing."
        ),
    )
    nickname = models.TextField(
        max_length=5000,
        default="",
        blank=True,
        help_text="A brief description of the plan, hidden from customers.",
    )
    product = StripeForeignKey(
        "Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The product whose pricing this plan determines.",
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
    transform_usage = JSONField(
        null=True,
        blank=True,
        help_text=(
            "Apply a transformation to the reported usage or set quantity "
            "before computing the billed price. Cannot be combined with `tiers`."
        ),
    )
    trial_period_days = models.IntegerField(
        null=True,
        blank=True,
        help_text=(
            "Number of trial period days granted when subscribing a customer "
            "to this plan. Null if the plan has no trial period."
        ),
    )
    usage_type = StripeEnumField(
        enum=enums.PriceUsageType,
        default=enums.PriceUsageType.licensed,
        help_text=(
            "Configures how the quantity per period should be determined, "
            "can be either `metered` or `licensed`. `licensed` will automatically "
            "bill the `quantity` set for a plan when adding it to a subscription, "
            "`metered` will aggregate the total usage based on usage records. "
            "Defaults to `licensed`."
        ),
    )

    class Meta(object):
        ordering = ["amount"]

    @classmethod
    def get_or_create(cls, **kwargs):
        """Get or create a Plan."""

        try:
            return Plan.objects.get(id=kwargs["id"]), False
        except Plan.DoesNotExist:
            return cls.create(**kwargs), True

    @classmethod
    def create(cls, **kwargs):
        # A few minor things are changed in the api-version of the create call
        api_kwargs = dict(kwargs)
        api_kwargs["amount"] = int(api_kwargs["amount"] * 100)

        if isinstance(api_kwargs.get("product"), StripeModel):
            api_kwargs["product"] = api_kwargs["product"].id

        stripe_plan = cls._api_create(**api_kwargs)
        api_key = api_kwargs.get("api_key") or djstripe_settings.STRIPE_SECRET_KEY
        plan = cls.sync_from_stripe_data(stripe_plan, api_key=api_key)

        return plan

    def __str__(self):
        if self.product and self.product.name:
            return f"{self.human_readable_price} for {self.product.name}"
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
            tier_1 = self.tiers[0]
            flat_amount_tier_1 = tier_1["flat_amount"]
            formatted_unit_amount_tier_1 = get_friendly_currency_amount(
                (tier_1["unit_amount"] or 0) / 100, self.currency
            )
            amount = f"Starts at {formatted_unit_amount_tier_1} per unit"

            # stripe shows flat fee even if it is set to 0.00
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

    application_fee_percent = StripePercentField(
        null=True,
        blank=True,
        help_text="A positive decimal that represents the fee percentage of the "
        "subscription invoice amount that will be transferred to the application "
        "owner's Stripe account each billing period.",
    )
    billing_cycle_anchor = StripeDateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Determines the date of the first full invoice, and, for plans "
            "with `month` or `year` intervals, the day of the month for subsequent "
            "invoices."
        ),
    )
    billing_thresholds = JSONField(
        null=True,
        blank=True,
        help_text="Define thresholds at which an invoice will be sent, and the "
        "subscription advanced to a new billing period.",
    )
    cancel_at = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="A date in the future at which the subscription will automatically "
        "get canceled.",
    )
    cancel_at_period_end = models.BooleanField(
        default=False,
        help_text="If the subscription has been canceled with the ``at_period_end`` "
        "flag set to true, ``cancel_at_period_end`` on the subscription will be true. "
        "You can use this attribute to determine whether a subscription that has a "
        "status of active is scheduled to be canceled at the end of the "
        "current period.",
    )
    canceled_at = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="If the subscription has been canceled, the date of that "
        "cancellation. If the subscription was canceled with ``cancel_at_period_end``, "
        "canceled_at will still reflect the date of the initial cancellation request, "
        "not the end of the subscription period when the subscription is automatically "
        "moved to a canceled state.",
    )
    collection_method = StripeEnumField(
        enum=enums.InvoiceCollectionMethod,
        help_text="Either `charge_automatically`, or `send_invoice`. When charging "
        "automatically, Stripe will attempt to pay this subscription at the end of the "
        "cycle using the default source attached to the customer. "
        "When sending an invoice, Stripe will email your customer an invoice with "
        "payment instructions.",
    )
    current_period_end = StripeDateTimeField(
        help_text="End of the current period for which the subscription has been "
        "invoiced. At the end of this period, a new invoice will be created."
    )
    current_period_start = StripeDateTimeField(
        help_text="Start of the current period for which the subscription has "
        "been invoiced."
    )
    customer = StripeForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        related_name="subscriptions",
        help_text="The customer associated with this subscription.",
    )
    days_until_due = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of days a customer has to pay invoices generated by this "
        "subscription. This value will be `null` for subscriptions where "
        "`billing=charge_automatically`.",
    )
    default_payment_method = StripeForeignKey(
        "PaymentMethod",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="The default payment method for the subscription. "
        "It must belong to the customer associated with the subscription. "
        "If not set, invoices will use the default payment method in the "
        "customer's invoice settings.",
    )
    default_source = PaymentMethodForeignKey(
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
        help_text="The default payment source for the subscription. "
        "It must belong to the customer associated with the subscription "
        "and be in a chargeable state. If not set, defaults to the customer's "
        "default source.",
    )
    default_tax_rates = models.ManyToManyField(
        "TaxRate",
        # explicitly specify the joining table name as though the joining model
        # was defined with through="DjstripeSubscriptionDefaultTaxRate"
        db_table="djstripe_djstripesubscriptiondefaulttaxrate",
        related_name="+",
        blank=True,
        help_text="The tax rates that will apply to any subscription item "
        "that does not have tax_rates set. Invoices created will have their "
        "default_tax_rates populated from the subscription.",
    )
    discount = JSONField(
        null=True,
        blank=True,
        help_text="Describes the current discount applied to this subscription, if there is one. When billing, a discount applied to a subscription overrides a discount applied on a customer-wide basis.",
    )
    ended_at = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="If the subscription has ended (either because it was canceled or "
        "because the customer was switched to a subscription to a new plan), "
        "the date the subscription ended.",
    )
    latest_invoice = StripeForeignKey(
        "Invoice",
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
        help_text="The most recent invoice this subscription has generated.",
    )
    next_pending_invoice_item_invoice = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="Specifies the approximate timestamp on which any pending "
        "invoice items will be billed according to the schedule provided at "
        "pending_invoice_item_interval.",
    )
    pause_collection = JSONField(
        null=True,
        blank=True,
        help_text="If specified, payment collection for this subscription will be paused.",
    )
    pending_invoice_item_interval = JSONField(
        null=True,
        blank=True,
        help_text="Specifies an interval for how often to bill for any "
        "pending invoice items. It is analogous to calling Create an invoice "
        "for the given subscription at the specified interval.",
    )
    pending_setup_intent = StripeForeignKey(
        "SetupIntent",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="setup_intents",
        help_text="We can use this SetupIntent to collect user authentication "
        "when creating a subscription without immediate payment or updating a "
        "subscription's payment method, allowing you to "
        "optimize for off-session payments.",
    )
    pending_update = JSONField(
        null=True,
        blank=True,
        help_text="If specified, pending updates that will be applied to the "
        "subscription once the latest_invoice has been paid.",
    )
    plan = models.ForeignKey(
        "Plan",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        help_text="The plan associated with this subscription. This value will be "
        "`null` for multi-plan subscriptions",
    )
    proration_behavior = StripeEnumField(
        enum=enums.SubscriptionProrationBehavior,
        help_text="Determines how to handle prorations when the billing cycle changes (e.g., when switching plans, resetting billing_cycle_anchor=now, or starting a trial), or if an item’s quantity changes",
        default=enums.SubscriptionProrationBehavior.create_prorations,
        blank=True,
    )
    proration_date = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="If set, the proration will be calculated as though the subscription was updated at the given time. This can be used to apply exactly the same proration that was previewed with upcoming invoice endpoint. It can also be used to implement custom proration logic, such as prorating by day instead of by second, by providing the time that you wish to use for proration calculations",
    )
    quantity = models.IntegerField(
        null=True,
        blank=True,
        help_text="The quantity applied to this subscription. This value will be "
        "`null` for multi-plan subscriptions",
    )
    schedule = models.ForeignKey(
        "SubscriptionSchedule",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        help_text="The schedule associated with this subscription.",
    )
    start_date = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="Date when the subscription was first created. The date "
        "might differ from the created date due to backdating.",
    )
    status = StripeEnumField(
        enum=enums.SubscriptionStatus, help_text="The status of this subscription."
    )
    trial_end = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="If the subscription has a trial, the end of that trial.",
    )
    trial_start = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="If the subscription has a trial, the beginning of that trial.",
    )

    objects = SubscriptionManager()

    def __str__(self):

        subscriptions_lst = self.customer._get_valid_subscriptions()
        products_lst = [
            subscription.plan.product.name
            for subscription in subscriptions_lst
            if subscription and subscription.plan and subscription.plan.product
        ]

        return f"{self.customer} on {' and '.join(products_lst)}"

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
        if not kwargs.get("status"):
            # special case: https://stripe.com/docs/api/subscriptions/list#list_subscriptions-status
            # See Issue: https://github.com/dj-stripe/dj-stripe/issues/1763
            kwargs["status"] = "all"

        return super().api_list(api_key=api_key, **kwargs)

    def update(
        self,
        plan: Union[StripeModel, str] = None,
        prorate: bool = None,
        **kwargs,
    ):
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

        # In short: We used to have a `prorate` argument which defaulted to
        # a DJSTRIPE_PRORATION_POLICY setting.
        # This is overly complex and specific, so we are dropping support for this.
        # To override it, you can pass `proration_behavior`.
        # If instead you pass `prorate`, we will transform it until dj-stripe 2.8.
        # If you have DJSTRIPE_PRORATION_POLICY set, we will default to it for now.
        # In 2.8, we will ignore both of those and let Stripe figure it out.
        # Stripe's default proration policy is specified here:
        # https://stripe.com/docs/billing/subscriptions/prorations
        if "proration_behavior" not in kwargs:
            if prorate is not None:
                warnings.warn(
                    "The `prorate` parameter to Subscription.update() is deprecated "
                    "by Stripe. Use `proration_behavior` instead.\n"
                    "Read more: "
                    "https://stripe.com/docs/billing/subscriptions/prorations",
                    DeprecationWarning,
                )
            elif kwargs.get("subscription_prorate") is not None:
                warnings.warn(
                    "The `subscription_prorate` parameter to Subscription.update() is deprecated "
                    "by Stripe. Use `proration_behavior` instead.\n"
                    "Read more: "
                    "https://stripe.com/docs/billing/subscriptions/prorations",
                    DeprecationWarning,
                )

            else:
                prorate = djstripe_settings.PRORATION_POLICY
                if prorate is not None:
                    warnings.warn(
                        "The `DJSTRIPE_PRORATION_POLICY` setting is deprecated and will "
                        "be ignored in dj-stripe 2.8. "
                        "Specify `proration_behavior` instead."
                    )
                else:
                    prorate = False

            if prorate:
                kwargs.setdefault("proration_behavior", "create_prorations")
            else:
                kwargs.setdefault("proration_behavior", "none")
        elif prorate is not None:
            raise TypeError(
                "`prorate` argument must not be set when `proration_behavior` is specified"
            )

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
            stripe_subscription = self._api_update(cancel_at_period_end=True)
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

        return self.status in ["trialing", "active"]

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

        self.default_tax_rates.set(
            cls._stripe_object_to_default_tax_rates(
                target_cls=TaxRate, data=data, api_key=api_key
            )
        )


class SubscriptionItem(StripeModel):
    """
    Subscription items allow you to create customer subscriptions
    with more than one plan, making it easy to represent complex billing relationships.

    Stripe documentation: https://stripe.com/docs/api?lang=python#subscription_items
    """

    stripe_class = stripe.SubscriptionItem

    billing_thresholds = JSONField(
        null=True,
        blank=True,
        help_text="Define thresholds at which an invoice will be sent, and the "
        "related subscription advanced to a new billing period.",
    )
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
    proration_behavior = StripeEnumField(
        enum=enums.SubscriptionProrationBehavior,
        help_text="Determines how to handle prorations when the billing cycle changes (e.g., when switching plans, resetting billing_cycle_anchor=now, or starting a trial), or if an item’s quantity changes",
        default=enums.SubscriptionProrationBehavior.create_prorations,
        blank=True,
    )
    proration_date = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="If set, the proration will be calculated as though the subscription was updated at the given time. This can be used to apply exactly the same proration that was previewed with upcoming invoice endpoint. It can also be used to implement custom proration logic, such as prorating by day instead of by second, by providing the time that you wish to use for proration calculations",
    )
    quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "The quantity of the plan to which the customer should be subscribed."
        ),
    )
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
        help_text="The tax rates which apply to this subscription_item. When set, "
        "the default_tax_rates on the subscription do not apply to this "
        "subscription_item.",
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
        help_text="Object representing the start and end dates for the "
        "current phase of the subscription schedule, if it is `active`.",
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
        help_text="Behavior of the subscription schedule and underlying "
        "subscription when it ends.",
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
        help_text="The subscription once managed by this subscription schedule "
        "(if it is released).",
    )
    status = StripeEnumField(
        enum=enums.SubscriptionScheduleStatus,
        help_text="The present status of the subscription schedule. Possible "
        "values are `not_started`, `active`, `completed`, `released`, and "
        "`canceled`.",
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
            self.id, api_key=api_key, stripe_account=stripe_account, **kwargs
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
            self.id, api_key=api_key, stripe_account=stripe_account, **kwargs
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

    active = models.BooleanField(
        default=True,
        help_text="Whether the shipping rate can be used for new purchases. Defaults to true",
    )
    display_name = models.CharField(
        max_length=50,
        default="",
        blank=True,
        help_text="The name of the shipping rate, meant to be displayable to the customer. This will appear on CheckoutSessions.",
    )
    fixed_amount = JSONField(
        help_text="Describes a fixed amount to charge for shipping. Must be present if type is fixed_amount",
    )
    type = StripeEnumField(
        enum=enums.ShippingRateType,
        default=enums.ShippingRateType.fixed_amount,
        help_text=_(
            "The type of calculation to use on the shipping rate. Can only be fixed_amount for now."
        ),
    )
    delivery_estimate = JSONField(
        null=True,
        blank=True,
        help_text="The estimated range for how long shipping will take, meant to be displayable to the customer. This will appear on CheckoutSessions.",
    )
    tax_behavior = StripeEnumField(
        enum=enums.ShippingRateTaxBehavior,
        help_text=_(
            "Specifies whether the rate is considered inclusive of taxes or exclusive of taxes."
        ),
    )
    tax_code = StripeForeignKey(
        "TaxCode",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="The shipping tax code",
    )

    class Meta(StripeModel.Meta):
        verbose_name = "Shipping Rate"

    def __str__(self):
        amount = get_friendly_currency_amount(
            self.fixed_amount.get("amount") / 100, self.fixed_amount.get("currency")
        )
        if self.active:
            return f"{self.display_name} - {amount} (Active)"
        else:
            return f"{self.display_name} - {amount} (Archived)"


class TaxCode(StripeModel):
    """
    Tax codes classify goods and services for tax purposes.

    Stripe documentation: https://stripe.com/docs/api/tax_codes
    """

    stripe_class = stripe.TaxCode
    metadata = None

    name = models.CharField(
        max_length=128,
        help_text="A short name for the tax code.",
    )

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

    country = models.CharField(
        max_length=2,
        help_text="Two-letter ISO code representing the country of the tax ID.",
    )
    customer = StripeForeignKey(
        "djstripe.customer", on_delete=models.CASCADE, related_name="tax_ids"
    )
    type = StripeEnumField(
        enum=enums.TaxIdType, help_text="The status of this subscription."
    )
    value = models.CharField(max_length=50, help_text="Value of the tax ID.")
    verification = JSONField(help_text="Tax ID verification information.")

    def __str__(self):
        return f"{enums.TaxIdType.humanize(self.type)} {self.value} ({self.verification.get('status')})"

    class Meta(StripeModel.Meta):
        verbose_name = "Tax ID"

    @classmethod
    def _api_create(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        """
        Call the stripe API's create operation for this model.

        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """

        if not kwargs.get("id"):
            raise KeyError("Customer Object ID is missing")

        try:
            Customer.objects.get(id=kwargs["id"])
        except Customer.DoesNotExist:
            raise

        return stripe.Customer.create_tax_id(api_key=api_key, **kwargs)

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
        nested_id = self.id
        id = self.customer.id

        # Prefer passed in stripe_account if set.
        if not stripe_account:
            stripe_account = self._get_stripe_account_id(api_key)

        return stripe.Customer.retrieve_tax_id(
            id=id,
            nested_id=nested_id,
            api_key=api_key or self.default_api_key,
            expand=self.expand_fields,
            stripe_account=stripe_account,
        )

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
        return stripe.Customer.list_tax_ids(
            api_key=api_key, **kwargs
        ).auto_paging_iter()


class TaxRate(StripeModel):
    """
    Tax rates can be applied to invoices and subscriptions to collect tax.

    Stripe documentation: https://stripe.com/docs/api/tax_rates?lang=python
    """

    stripe_class = stripe.TaxRate
    stripe_dashboard_item_name = "tax-rates"

    active = models.BooleanField(
        default=True,
        help_text="Defaults to true. When set to false, this tax rate cannot be "
        "applied to objects in the API, but will still be applied to subscriptions "
        "and invoices that already have it set.",
    )
    country = models.CharField(
        max_length=2,
        default="",
        blank=True,
        help_text="Two-letter country code.",
    )
    display_name = models.CharField(
        max_length=50,
        default="",
        blank=True,
        help_text="The display name of the tax rates as it will appear to your "
        "customer on their receipt email, PDF, and the hosted invoice page.",
    )
    inclusive = models.BooleanField(
        help_text="This specifies if the tax rate is inclusive or exclusive."
    )
    jurisdiction = models.CharField(
        max_length=50,
        default="",
        blank=True,
        help_text="The jurisdiction for the tax rate.",
    )
    percentage = StripePercentField(
        decimal_places=4,
        max_digits=7,
        help_text="This represents the tax rate percent out of 100.",
    )
    state = models.CharField(
        max_length=2,
        default="",
        blank=True,
        help_text="ISO 3166-2 subdivision code, without country prefix.",
    )
    tax_type = models.CharField(
        default="",
        blank=True,
        max_length=50,
        help_text="The high-level tax type, such as vat, gst, sales_tax or custom.",
    )

    def __str__(self):
        return f"{self.display_name} at {self.percentage}%"

    class Meta(StripeModel.Meta):
        verbose_name = "Tax Rate"


class UsageRecord(StripeModel):
    """
    Usage records allow you to continually report usage and metrics to
    Stripe for metered billing of plans.

    Stripe documentation: https://stripe.com/docs/api?lang=python#usage_records
    """

    description = None
    metadata = None

    stripe_class = stripe.UsageRecord

    quantity = models.PositiveIntegerField(
        help_text=(
            "The quantity of the plan to which the customer should be subscribed."
        )
    )
    subscription_item = StripeForeignKey(
        "SubscriptionItem",
        on_delete=models.CASCADE,
        related_name="usage_records",
        help_text="The subscription item this usage record contains data for.",
    )

    timestamp = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="The timestamp for the usage event. This timestamp must be within the current billing period of the subscription of the provided subscription_item.",
    )

    action = StripeEnumField(
        enum=enums.UsageAction,
        default=enums.UsageAction.increment,
        help_text="When using increment the specified quantity will be added to the usage at the specified timestamp. The set action will overwrite the usage quantity at that timestamp. If the subscription has billing thresholds, increment is the only allowed value.",
    )

    def __str__(self):
        return f"Usage for {self.subscription_item} ({self.action}) is {self.quantity}"

    @classmethod
    def _api_create(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        """
        Call the stripe API's create operation for this model.

        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """

        if not kwargs.get("id"):
            raise KeyError("SubscriptionItem Object ID is missing")

        try:
            SubscriptionItem.objects.get(id=kwargs["id"])
        except SubscriptionItem.DoesNotExist:
            raise

        usage_stripe_data = stripe.SubscriptionItem.create_usage_record(
            api_key=api_key, **kwargs
        )

        # ! Hack: there is no way to retrieve a UsageRecord object from Stripe,
        # ! which is why we create and sync it right here
        cls.sync_from_stripe_data(usage_stripe_data, api_key=api_key)

        return usage_stripe_data

    @classmethod
    def create(cls, **kwargs):
        """
        A wrapper around _api_create() to allow one to create and sync UsageRecord Objects
        """
        return cls._api_create(**kwargs)


class UsageRecordSummary(StripeModel):
    """
    Usage record summaries provides usage information that's been summarized
    from multiple usage records and over a subscription billing period
    (e.g., 15 usage records in the month of September).
    Since new usage records can still be added, the returned summary information for the subscription item's ID
    should be seen as unstable until the subscription billing period ends.

    Stripe documentation: https://stripe.com/docs/api/usage_records/subscription_item_summary_list?lang=python
    """

    stripe_class = stripe.UsageRecordSummary

    description = None
    metadata = None

    invoice = StripeForeignKey(
        "Invoice",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="usage_record_summaries",
    )
    period = JSONField(
        null=True,
        blank=True,
        help_text="Subscription Billing period for the SubscriptionItem",
    )
    period_end = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="End of the Subscription Billing period for the SubscriptionItem",
    )
    period_start = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="Start of the Subscription Billing period for the SubscriptionItem",
    )
    total_usage = models.PositiveIntegerField(
        help_text=(
            "The quantity of the plan to which the customer should be subscribed."
        )
    )
    subscription_item = StripeForeignKey(
        "SubscriptionItem",
        on_delete=models.CASCADE,
        related_name="usage_record_summaries",
        help_text="The subscription item this usage record contains data for.",
    )

    def __str__(self):
        return f"Usage Summary for {self.subscription_item} ({self.invoice}) is {self.total_usage}"

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        data["period_start"] = data["period"]["start"]
        data["period_end"] = data["period"]["end"]

        return data

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
        if not kwargs.get("id"):
            raise KeyError("SubscriptionItem Object ID is missing")

        try:
            SubscriptionItem.objects.get(id=kwargs["id"])
        except SubscriptionItem.DoesNotExist:
            raise

        return stripe.SubscriptionItem.list_usage_record_summaries(
            api_key=api_key, **kwargs
        ).auto_paging_iter()
