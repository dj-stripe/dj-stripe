from copy import deepcopy

import stripe
from django.db import models
from django.utils import timezone
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from stripe.error import InvalidRequestError

from .. import enums
from .. import settings as djstripe_settings
from ..fields import (
	JSONField, StripeCurrencyCodeField, StripeDateTimeField,
	StripeDecimalCurrencyAmountField, StripeEnumField, StripeIdField, StripePercentField
)
from ..managers import SubscriptionManager
from ..utils import QuerySetMock, get_friendly_currency_amount
from .base import StripeModel


class Coupon(StripeModel):
	id = StripeIdField(max_length=500)
	amount_off = StripeDecimalCurrencyAmountField(
		null=True,
		blank=True,
		help_text="Amount that will be taken off the subtotal of any invoices for this customer.",
	)
	currency = StripeCurrencyCodeField(null=True, blank=True)
	duration = StripeEnumField(
		enum=enums.CouponDuration,
		help_text=(
			"Describes how long a customer who applies this coupon will get the discount."
		),
	)
	duration_in_months = models.PositiveIntegerField(
		null=True,
		blank=True,
		help_text="If `duration` is `repeating`, the number of months the coupon applies.",
	)
	max_redemptions = models.PositiveIntegerField(
		null=True,
		blank=True,
		help_text="Maximum number of times this coupon can be redeemed, in total, before it is no longer valid.",
	)
	name = models.TextField(
		max_length=5000,
		default="",
		blank=True,
		help_text=(
			"Name of the coupon displayed to customers on for instance invoices or receipts."
		),
	)
	percent_off = StripePercentField(
		null=True,
		blank=True,
		help_text=(
			"Percent that will be taken off the subtotal of any invoices for this customer "
			"for the duration of the coupon. For example, a coupon with percent_off of 50 "
			"will make a $100 invoice $50 instead."
		),
	)
	redeem_by = StripeDateTimeField(
		null=True,
		blank=True,
		help_text="Date after which the coupon can no longer be redeemed. Max 5 years in the future.",
	)
	times_redeemed = models.PositiveIntegerField(
		editable=False,
		default=0,
		help_text="Number of times this coupon has been applied to a customer.",
	)
	# valid = models.BooleanField(editable=False)

	# XXX
	DURATION_FOREVER = "forever"
	DURATION_ONCE = "once"
	DURATION_REPEATING = "repeating"

	class Meta:
		unique_together = ("id", "livemode")

	stripe_class = stripe.Coupon
	stripe_dashboard_item_name = "coupons"

	def __str__(self):
		if self.name:
			return self.name
		return self.human_readable

	@property
	def human_readable_amount(self):
		if self.percent_off:
			amount = "{percent_off}%".format(percent_off=self.percent_off)
		else:
			amount = get_friendly_currency_amount(self.amount_off or 0, self.currency)
		return "{amount} off".format(amount=amount)

	@property
	def human_readable(self):
		if self.duration == self.DURATION_REPEATING:
			if self.duration_in_months == 1:
				duration = "for {duration_in_months} month"
			else:
				duration = "for {duration_in_months} months"
			duration = duration.format(duration_in_months=self.duration_in_months)
		else:
			duration = self.duration
		return "{amount} {duration}".format(
			amount=self.human_readable_amount, duration=duration
		)


class Invoice(StripeModel):
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

	Stripe documentation: https://stripe.com/docs/api/python#invoices
	"""

	stripe_class = stripe.Invoice
	stripe_dashboard_item_name = "invoices"

	amount_due = StripeDecimalCurrencyAmountField(
		help_text="Final amount due at this time for this invoice. If the invoice's total is smaller than the minimum "
		"charge amount, for example, or if there is account credit that can be applied to the invoice, the amount_due "
		"may be 0. If there is a positive starting_balance for the invoice (the customer owes money), the amount_due "
		"will also take that into account. The charge that gets generated for the invoice will be for the amount "
		"specified in amount_due."
	)
	amount_paid = StripeDecimalCurrencyAmountField(
		null=True,  # XXX: This is not nullable, but it's a new field
		help_text="The amount, in cents, that was paid.",
	)
	amount_remaining = StripeDecimalCurrencyAmountField(
		null=True,  # XXX: This is not nullable, but it's a new field
		help_text="The amount, in cents, that was paid.",
	)
	application_fee = StripeDecimalCurrencyAmountField(
		null=True,
		help_text="The fee in cents that will be applied to the invoice and transferred to the application owner's "
		"Stripe account when the invoice is paid.",
	)
	attempt_count = models.IntegerField(
		help_text="Number of payment attempts made for this invoice, from the perspective of the payment retry "
		"schedule. Any payment attempt counts as the first attempt, and subsequently only automatic retries "
		"increment the attempt count. In other words, manual payment attempts after the first attempt do not affect "
		"the retry schedule."
	)
	attempted = models.BooleanField(
		default=False,
		help_text="Whether or not an attempt has been made to pay the invoice. An invoice is not attempted until 1 "
		"hour after the ``invoice.created`` webhook, for example, so you might not want to display that invoice as "
		"unpaid to your users.",
	)
	billing = StripeEnumField(
		enum=enums.InvoiceBilling,
		null=True,
		help_text=(
			"When charging automatically, Stripe will attempt to pay this invoice"
			"using the default source attached to the customer. "
			"When sending an invoice, Stripe will email this invoice to the customer "
			"with payment instructions."
		),
	)
	charge = models.OneToOneField(
		"Charge",
		on_delete=models.CASCADE,
		null=True,
		related_name="latest_invoice",
		help_text="The latest charge generated for this invoice, if any.",
	)
	closed = models.BooleanField(
		default=False,
		help_text="Whether or not the invoice is still trying to collect payment. An invoice is closed if it's either "
		"paid or it has been marked closed. A closed invoice will no longer attempt to collect payment.",
	)
	currency = StripeCurrencyCodeField()
	customer = models.ForeignKey(
		"Customer",
		on_delete=models.CASCADE,
		related_name="invoices",
		help_text="The customer associated with this invoice.",
	)
	date = StripeDateTimeField(help_text="The date on the invoice.")
	# TODO: discount
	due_date = StripeDateTimeField(
		null=True,
		help_text=(
			"The date on which payment for this invoice is due. "
			"This value will be null for invoices where billing=charge_automatically."
		),
	)
	ending_balance = models.IntegerField(
		null=True,
		help_text="Ending customer balance after attempting to pay invoice. If the invoice has not been attempted "
		"yet, this will be null.",
	)
	forgiven = models.BooleanField(
		default=False,
		help_text="Whether or not the invoice has been forgiven. Forgiving an invoice instructs us to update the "
		"subscription status as if the invoice were successfully paid. Once an invoice has been forgiven, it cannot "
		"be unforgiven or reopened.",
	)
	hosted_invoice_url = models.TextField(
		max_length=799,
		default="",
		blank=True,
		help_text=(
			"The URL for the hosted invoice page, which allows customers to view and pay an invoice. "
			"If the invoice has not been frozen yet, this will be null."
		),
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
	next_payment_attempt = StripeDateTimeField(
		null=True, help_text="The time at which payment will next be attempted."
	)
	number = models.CharField(
		max_length=64,
		default="",
		blank=True,
		help_text=(
			"A unique, identifying string that appears on emails sent to the customer for this invoice. "
			"This starts with the customer’s unique invoice_prefix if it is specified."
		),
	)
	paid = models.BooleanField(
		default=False, help_text="The time at which payment will next be attempted."
	)
	period_end = StripeDateTimeField(
		help_text="End of the usage period during which invoice items were added to this invoice."
	)
	period_start = StripeDateTimeField(
		help_text="Start of the usage period during which invoice items were added to this invoice."
	)
	receipt_number = models.CharField(
		max_length=64,
		null=True,
		help_text=(
			"This is the transaction number that appears on email receipts sent for this invoice."
		),
	)
	starting_balance = models.IntegerField(
		help_text="Starting customer balance before attempting to pay invoice. If the invoice has not been attempted "
		"yet, this will be the current customer balance."
	)
	statement_descriptor = models.CharField(
		max_length=22,
		default="",
		blank=True,
		help_text="An arbitrary string to be displayed on your customer's credit card statement. The statement "
		"description may not include <>\"' characters, and will appear on your customer's statement in capital "
		"letters. Non-ASCII characters are automatically stripped. While most banks display this information "
		"consistently, some may display it incorrectly or not at all.",
	)
	subscription = models.ForeignKey(
		"Subscription",
		null=True,
		related_name="invoices",
		on_delete=models.SET_NULL,
		help_text="The subscription that this invoice was prepared for, if any.",
	)
	subscription_proration_date = StripeDateTimeField(
		null=True,
		blank=True,
		help_text="Only set for upcoming invoices that preview prorations. The time used to calculate prorations.",
	)
	subtotal = StripeDecimalCurrencyAmountField(
		help_text="Only set for upcoming invoices that preview prorations. The time used to calculate prorations."
	)
	tax = StripeDecimalCurrencyAmountField(
		null=True,
		blank=True,
		help_text="The amount of tax included in the total, calculated from ``tax_percent`` and the subtotal. If no "
		"``tax_percent`` is defined, this value will be null.",
	)
	tax_percent = StripePercentField(
		null=True,
		help_text="This percentage of the subtotal has been added to the total amount of the invoice, including "
		"invoice line items and discounts. This field is inherited from the subscription's ``tax_percent`` field, "
		"but can be changed before the invoice is paid. This field defaults to null.",
	)
	total = StripeDecimalCurrencyAmountField("Total after discount.")
	webhooks_delivered_at = StripeDateTimeField(
		null=True,
		help_text=(
			"The time at which webhooks for this invoice were successfully delivered "
			"(if the invoice had no webhooks to deliver, this will match `date`). "
			"Invoice payment is delayed until webhooks are delivered, or until all "
			"webhook delivery attempts have been exhausted."
		),
	)

	class Meta(object):
		ordering = ["-date"]

	def __str__(self):
		return "Invoice #{number}".format(
			number=self.number or self.receipt_number or self.id
		)

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
		**kwargs
	):
		"""
		Gets the upcoming preview invoice (singular) for a customer.

		At any time, you can preview the upcoming
		invoice for a customer. This will show you all the charges that are
		pending, including subscription renewal charges, invoice item charges,
		etc. It will also show you any discount that is applicable to the
		customer. (Source: https://stripe.com/docs/api#upcoming_invoice)

		.. important:: Note that when you are viewing an upcoming invoice, you are simply viewing a preview.

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
		:rtype: UpcomingInvoice
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
				**kwargs
			)
		except InvalidRequestError as exc:
			if str(exc) != "Nothing to invoice for customer":
				raise
			return

		# Workaround for "id" being missing (upcoming invoices don't persist).
		upcoming_stripe_invoice["id"] = "upcoming"

		return UpcomingInvoice._create_from_stripe_object(upcoming_stripe_invoice, save=False)

	def retry(self):
		""" Retry payment on this invoice if it isn't paid, closed, or forgiven."""

		if not self.paid and not self.forgiven and not self.closed:
			stripe_invoice = self.api_retrieve()
			updated_stripe_invoice = (
				stripe_invoice.pay()
			)  # pay() throws an exception if the charge is not successful.
			type(self).sync_from_stripe_data(updated_stripe_invoice)
			return True
		return False

	STATUS_PAID = "Paid"
	STATUS_FORGIVEN = "Forgiven"
	STATUS_CLOSED = "Closed"
	STATUS_OPEN = "Open"

	@property
	def status(self):
		""" Attempts to label this invoice with a status. Note that an invoice can be more than one of the choices.
			We just set a priority on which status appears.
		"""

		if self.paid:
			return self.STATUS_PAID
		if self.forgiven:
			return self.STATUS_FORGIVEN
		if self.closed:
			return self.STATUS_CLOSED
		return self.STATUS_OPEN

	def get_stripe_dashboard_url(self):
		return self.customer.get_stripe_dashboard_url()

	def _attach_objects_post_save_hook(self, cls, data, pending_relations=None):
		super()._attach_objects_post_save_hook(cls, data, pending_relations=pending_relations)

		# InvoiceItems need a saved invoice because they're associated via a
		# RelatedManager, so this must be done as part of the post save hook.
		cls._stripe_object_to_invoice_items(target_cls=InvoiceItem, data=data, invoice=self)

	@property
	def plan(self):
		""" Gets the associated plan for this invoice.

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
		:rtype: ``djstripe.Plan``
		"""

		for invoiceitem in self.invoiceitems.all():
			if invoiceitem.plan:
				return invoiceitem.plan

		if self.subscription:
			return self.subscription.plan


class UpcomingInvoice(Invoice):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._invoiceitems = []

	def get_stripe_dashboard_url(self):
		return ""

	def _attach_objects_hook(self, cls, data):
		super()._attach_objects_hook(cls, data)
		self._invoiceitems = cls._stripe_object_to_invoice_items(
			target_cls=InvoiceItem, data=data, invoice=self
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

		return QuerySetMock.from_iterable(InvoiceItem, self._invoiceitems)

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

	Stripe documentation: https://stripe.com/docs/api/python#invoiceitems
	"""

	stripe_class = stripe.InvoiceItem

	amount = StripeDecimalCurrencyAmountField(help_text="Amount invoiced.")
	currency = StripeCurrencyCodeField()
	customer = models.ForeignKey(
		"Customer",
		on_delete=models.CASCADE,
		related_name="invoiceitems",
		help_text="The customer associated with this invoiceitem.",
	)
	date = StripeDateTimeField(help_text="The date on the invoiceitem.")
	discountable = models.BooleanField(
		default=False,
		help_text="If True, discounts will apply to this invoice item. Always False for prorations.",
	)
	invoice = models.ForeignKey(
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
		related_name="invoiceitems",
		on_delete=models.SET_NULL,
		help_text="If the invoice item is a proration, the plan of the subscription for which the proration was "
		"computed.",
	)
	proration = models.BooleanField(
		default=False,
		help_text="Whether or not the invoice item was created automatically as a proration adjustment when the "
		"customer switched plans.",
	)
	quantity = models.IntegerField(
		null=True,
		blank=True,
		help_text="If the invoice item is a proration, the quantity of the subscription for which the proration "
		"was computed.",
	)
	subscription = models.ForeignKey(
		"Subscription",
		null=True,
		related_name="invoiceitems",
		on_delete=models.SET_NULL,
		help_text="The subscription that this invoice item has been created for, if any.",
	)
	# XXX: subscription_item

	@classmethod
	def _manipulate_stripe_object_hook(cls, data):
		data["period_start"] = data["period"]["start"]
		data["period_end"] = data["period"]["end"]

		return data

	@classmethod
	def sync_from_stripe_data(cls, data, field_name="id"):
		# sync the Invoice first to avoid recursive Charge/Invoice loop
		Invoice.sync_from_stripe_data(
			data={"invoice": data.get("invoice")}, field_name="invoice"
		)

		return super().sync_from_stripe_data(data, field_name=field_name)

	def __str__(self):
		if self.plan and self.plan.product:
			return self.plan.product.name or str(self.plan)
		return super().__str__()

	@classmethod
	def is_valid_object(cls, data):
		return data["object"] in ("invoiceitem", "line_item")

	def get_stripe_dashboard_url(self):
		return self.invoice.get_stripe_dashboard_url()

	def str_parts(self):
		return [
			"amount={amount}".format(amount=self.amount),
			"date={date}".format(date=self.date),
		] + super().str_parts()


class Plan(StripeModel):
	"""
	A subscription plan contains the pricing information for different
	products and feature levels on your site.

	Stripe documentation: https://stripe.com/docs/api/python#plans)
	"""

	stripe_class = stripe.Plan
	stripe_dashboard_item_name = "plans"

	active = models.BooleanField(
		help_text="Whether the plan is currently available for new subscriptions."
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
		help_text="Amount to be charged on the interval specified."
	)
	billing_scheme = StripeEnumField(
		enum=enums.PlanBillingScheme,
		default="",
		blank=True,
		help_text=(
			"Describes how to compute the price per period. Either `per_unit` or `tiered`. "
			"`per_unit` indicates that the fixed amount (specified in amount) will be charged "
			"per unit in quantity (for plans with `usage_type=licensed`), or per unit of total "
			"usage (for plans with `usage_type=metered`). "
			"`tiered` indicates that the unit pricing will be computed using a tiering strategy "
			"as defined using the tiers and tiers_mode attributes."
		),
	)
	currency = StripeCurrencyCodeField()
	interval = StripeEnumField(
		enum=enums.PlanInterval,
		help_text="The frequency with which a subscription should be billed.",
	)
	interval_count = models.IntegerField(
		null=True,
		help_text=(
			"The number of intervals (specified in the interval property) between each subscription billing."
		),
	)
	nickname = models.TextField(
		max_length=5000,
		default="",
		blank=True,
		help_text="A brief description of the plan, hidden from customers.",
	)
	product = models.ForeignKey(
		"Product",
		on_delete=models.SET_NULL,
		null=True,
		help_text=("The product whose pricing this plan determines."),
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
		enum=enums.PlanTiersMode,
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
		help_text=(
			"Number of trial period days granted when subscribing a customer to this plan. "
			"Null if the plan has no trial period."
		),
	)
	usage_type = StripeEnumField(
		enum=enums.PlanUsageType,
		default=enums.PlanUsageType.licensed,
		help_text=(
			"Configures how the quantity per period should be determined, can be either"
			"`metered` or `licensed`. `licensed` will automatically bill the `quantity` "
			"set for a plan when adding it to a subscription, `metered` will aggregate "
			"the total usage based on usage records. Defaults to `licensed`."
		),
	)

	# Legacy fields (pre 2017-08-15)
	name = models.TextField(
		null=True,
		blank=True,
		help_text="Name of the plan, to be displayed on invoices and in the web interface.",
	)
	statement_descriptor = models.CharField(
		max_length=22,
		null=True,
		blank=True,
		help_text=(
			"An arbitrary string to be displayed on your customer's credit card statement. The statement "
			"description may not include <>\"' characters, and will appear on your customer's statement in capital "
			"letters. Non-ASCII characters are automatically stripped. While most banks display this information "
			"consistently, some may display it incorrectly or not at all."
		),
	)

	class Meta(object):
		ordering = ["amount"]

	@classmethod
	def get_or_create(cls, **kwargs):
		""" Get or create a Plan."""

		try:
			return Plan.objects.get(id=kwargs["id"]), False
		except Plan.DoesNotExist:
			return cls.create(**kwargs), True

	@classmethod
	def create(cls, **kwargs):
		# A few minor things are changed in the api-version of the create call
		api_kwargs = dict(kwargs)
		api_kwargs["amount"] = int(api_kwargs["amount"] * 100)
		cls._api_create(**api_kwargs)

		plan = Plan.objects.create(**kwargs)

		return plan

	def __str__(self):
		return self.name or self.nickname or self.id

	@property
	def amount_in_cents(self):
		return int(self.amount * 100)

	@property
	def human_readable_price(self):
		amount = get_friendly_currency_amount(self.amount, self.currency)
		interval_count = self.interval_count

		if interval_count == 1:
			interval = {
				"day": _("day"),
				"week": _("week"),
				"month": _("month"),
				"year": _("year"),
			}[self.interval]
			template = _("{amount}/{interval}")
		else:
			interval = {
				"day": _("days"),
				"week": _("weeks"),
				"month": _("months"),
				"year": _("years"),
			}[self.interval]
			template = _("{amount} every {interval_count} {interval}")

		return format_lazy(
			template, amount=amount, interval=interval, interval_count=interval_count
		)

	# TODO: Move this type of update to the model's save() method so it happens automatically
	# Also, block other fields from being saved.
	def update_name(self):
		"""
		Update the name of the Plan in Stripe and in the db.

		Assumes the object being called has the name attribute already
		reset, but has not been saved.

		Stripe does not allow for update of any other Plan attributes besides name.
		"""

		p = self.api_retrieve()
		p.name = self.name
		p.save()

		self.save()


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
	will be attempted (invoices will be created, but then immediately automatically closed.
	Additionally, updating customer card details will not lead to Stripe retrying the
	latest invoice.).
	After receiving updated card details from a customer, you may choose to reopen and
	pay their closed invoices.

	Stripe documentation: https://stripe.com/docs/api/python#subscriptions
	"""

	stripe_class = stripe.Subscription
	stripe_dashboard_item_name = "subscriptions"

	application_fee_percent = StripePercentField(
		null=True,
		blank=True,
		help_text="A positive decimal that represents the fee percentage of the subscription invoice amount that "
		"will be transferred to the application owner's Stripe account each billing period.",
	)
	billing = StripeEnumField(
		enum=enums.InvoiceBilling,
		help_text=(
			"Either `charge_automatically`, or `send_invoice`. When charging automatically, "
			"Stripe will attempt to pay this subscription at the end of the cycle using the "
			"default source attached to the customer. When sending an invoice, Stripe will "
			"email your customer an invoice with payment instructions."
		),
	)
	billing_cycle_anchor = StripeDateTimeField(
		null=True,
		blank=True,
		help_text=(
			"Determines the date of the first full invoice, and, for plans with `month` or "
			"`year` intervals, the day of the month for subsequent invoices."
		),
	)
	cancel_at_period_end = models.BooleanField(
		default=False,
		help_text="If the subscription has been canceled with the ``at_period_end`` flag set to true, "
		"``cancel_at_period_end`` on the subscription will be true. You can use this attribute to determine whether "
		"a subscription that has a status of active is scheduled to be canceled at the end of the current period.",
	)
	canceled_at = StripeDateTimeField(
		null=True,
		blank=True,
		help_text="If the subscription has been canceled, the date of that cancellation. If the subscription was "
		"canceled with ``cancel_at_period_end``, canceled_at will still reflect the date of the initial cancellation "
		"request, not the end of the subscription period when the subscription is automatically moved to a canceled "
		"state.",
	)
	current_period_end = StripeDateTimeField(
		help_text="End of the current period for which the subscription has been invoiced. At the end of this period, "
		"a new invoice will be created."
	)
	current_period_start = StripeDateTimeField(
		help_text="Start of the current period for which the subscription has been invoiced."
	)
	customer = models.ForeignKey(
		"Customer",
		on_delete=models.CASCADE,
		related_name="subscriptions",
		help_text="The customer associated with this subscription.",
	)
	days_until_due = models.IntegerField(
		null=True,
		blank=True,
		help_text=(
			"Number of days a customer has to pay invoices generated by this subscription. "
			"This value will be `null` for subscriptions where `billing=charge_automatically`."
		),
	)
	# TODO: discount
	ended_at = StripeDateTimeField(
		null=True,
		blank=True,
		help_text=(
			"If the subscription has ended (either because it was canceled or because the customer was switched "
			"to a subscription to a new plan), the date the subscription ended."
		),
	)
	plan = models.ForeignKey(
		"Plan",
		null=True,
		blank=True,
		on_delete=models.CASCADE,
		related_name="subscriptions",
		help_text="The plan associated with this subscription. This value will be `null` for multi-plan subscriptions",
	)
	quantity = models.IntegerField(
		null=True,
		blank=True,
		help_text="The quantity applied to this subscription. This value will be `null` for multi-plan subscriptions",
	)
	start = StripeDateTimeField(help_text="Date the subscription started.")
	status = StripeEnumField(
		enum=enums.SubscriptionStatus, help_text="The status of this subscription."
	)
	tax_percent = StripePercentField(
		null=True,
		blank=True,
		help_text="A positive decimal (with at most two decimal places) between 1 and 100. This represents the "
		"percentage of the subscription invoice subtotal that will be calculated and added as tax to the final "
		"amount each billing period.",
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
		return "{customer} on {plan}".format(customer=str(self.customer), plan=str(self.plan))

	def update(
		self,
		plan=None,
		application_fee_percent=None,
		coupon=None,
		prorate=djstripe_settings.PRORATION_POLICY,
		proration_date=None,
		metadata=None,
		quantity=None,
		tax_percent=None,
		trial_end=None,
	):
		"""
		See `Customer.subscribe() <#djstripe.models.Customer.subscribe>`__

		:param plan: The plan to which to subscribe the customer.
		:type plan: Plan or string (plan ID)
		:param prorate: Whether or not to prorate when switching plans. Default is True.
		:type prorate: boolean
		:param proration_date:
			If set, the proration will be calculated as though the subscription was updated at the
			given time. This can be used to apply exactly the same proration that was previewed
			with upcoming invoice endpoint. It can also be used to implement custom proration
			logic, such as prorating by day instead of by second, by providing the time that you
			wish to use for proration calculations.
		:type proration_date: datetime

		.. note:: The default value for ``prorate`` is the DJSTRIPE_PRORATION_POLICY setting.

		.. important:: Updating a subscription by changing the plan or quantity creates a new ``Subscription`` in \
		Stripe (and dj-stripe).
		"""

		# Convert Plan to id
		if plan is not None and isinstance(plan, StripeModel):
			plan = plan.id

		kwargs = deepcopy(locals())
		del kwargs["self"]

		stripe_subscription = self.api_retrieve()

		for kwarg, value in kwargs.items():
			if value is not None:
				setattr(stripe_subscription, kwarg, value)

		return Subscription.sync_from_stripe_data(stripe_subscription.save())

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

		return self.update(prorate=False, trial_end=period_end)

	def cancel(self, at_period_end=djstripe_settings.CANCELLATION_AT_PERIOD_END):
		"""
		Cancels this subscription. If you set the at_period_end parameter to true, the subscription will remain active
		until the end of the period, at which point it will be canceled and not renewed. By default, the subscription
		is terminated immediately. In either case, the customer will not be charged again for the subscription. Note,
		however, that any pending invoice items that you've created will still be charged for at the end of the period
		unless manually deleted. If you've set the subscription to cancel at period end, any pending prorations will
		also be left in place and collected at the end of the period, but if the subscription is set to cancel
		immediately, pending prorations will be removed.

		By default, all unpaid invoices for the customer will be closed upon subscription cancellation. We do this in
		order to prevent unexpected payment retries once the customer has canceled a subscription. However, you can
		reopen the invoices manually after subscription cancellation to have us proceed with automatic retries, or you
		could even re-attempt payment yourself on all unpaid invoices before allowing the customer to cancel the
		subscription at all.

		:param at_period_end: A flag that if set to true will delay the cancellation of the subscription until the end
			of the current period. Default is False.
		:type at_period_end: boolean

		.. important:: If a subscription is cancelled during a trial period, the ``at_period_end`` flag will be \
		overridden to False so that the trial ends immediately and the customer's card isn't charged.
		"""

		# If plan has trial days and customer cancels before
		# trial period ends, then end subscription now,
		# i.e. at_period_end=False
		if self.trial_end and self.trial_end > timezone.now():
			at_period_end = False

		if at_period_end:
			stripe_subscription = self.api_retrieve()
			stripe_subscription.cancel_at_period_end = True
			stripe_subscription.save()
		else:
			try:
				stripe_subscription = self._api_delete()
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

		return Subscription.sync_from_stripe_data(stripe_subscription)

	def reactivate(self):
		"""
		Reactivates this subscription.

		If a customer's subscription is canceled with ``at_period_end`` set to True and it has not yet reached the end
		of the billing period, it can be reactivated. Subscriptions canceled immediately cannot be reactivated.
		(Source: https://stripe.com/docs/subscriptions/canceling-pausing)

		.. warning:: Reactivating a fully canceled Subscription will fail silently. Be sure to check the returned \
		Subscription's status.
		"""
		stripe_subscription = self.api_retrieve()
		stripe_subscription.plan = self.plan.id
		stripe_subscription.cancel_at_period_end = False

		return Subscription.sync_from_stripe_data(stripe_subscription.save())

	def is_period_current(self):
		""" Returns True if this subscription's period is current, false otherwise."""

		return self.current_period_end > timezone.now() or (
			self.trial_end and self.trial_end > timezone.now()
		)

	def is_status_current(self):
		""" Returns True if this subscription's status is current (active or trialing), false otherwise."""

		return self.status in ["trialing", "active"]

	def is_status_temporarily_current(self):
		"""
		A status is temporarily current when the subscription is canceled with the ``at_period_end`` flag.
		The subscription is still active, but is technically canceled and we're just waiting for it to run out.

		You could use this method to give customers limited service after they've canceled. For example, a video
		on demand service could only allow customers to download their libraries  and do nothing else when their
		subscription is temporarily current.
		"""

		return (
			self.canceled_at and self.start < self.canceled_at and self.cancel_at_period_end
		)

	def is_valid(self):
		""" Returns True if this subscription's status and period are current, false otherwise."""

		if not self.is_status_current():
			return False

		if not self.is_period_current():
			return False

		return True

	def _attach_objects_post_save_hook(self, cls, data, pending_relations=None):
		super()._attach_objects_post_save_hook(cls, data, pending_relations=pending_relations)

		cls._stripe_object_to_subscription_items(
			target_cls=SubscriptionItem, data=data, subscription=self
		)


class SubscriptionItem(StripeModel):
	"""
	Subscription items allow you to create customer subscriptions
	with more than one plan, making it easy to represent complex billing relationships.

	Stripe documentation: https://stripe.com/docs/api#subscription_items
	"""

	stripe_class = stripe.SubscriptionItem

	plan = models.ForeignKey(
		"Plan",
		on_delete=models.CASCADE,
		related_name="subscription_items",
		help_text="The plan the customer is subscribed to.",
	)
	quantity = models.PositiveIntegerField(
		help_text=("The quantity of the plan to which the customer should be subscribed.")
	)
	subscription = models.ForeignKey(
		"Subscription",
		on_delete=models.CASCADE,
		related_name="items",
		help_text="The subscription this subscription item belongs to.",
	)


class UsageRecord(StripeModel):
	"""
	Usage records allow you to continually report usage and metrics to
	Stripe for metered billing of plans.

	Stripe documentation: https://stripe.com/docs/api#usage_records
	"""

	quantity = models.PositiveIntegerField(
		help_text=("The quantity of the plan to which the customer should be subscribed.")
	)
	subscription_item = models.ForeignKey(
		"SubscriptionItem",
		on_delete=models.CASCADE,
		related_name="usage_records",
		help_text="The subscription item this usage record contains data for.",
	)
