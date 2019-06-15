import operator
from collections import OrderedDict

from django.utils.translation import gettext_lazy as _


class EnumMetaClass(type):
	@classmethod
	def __prepare__(self, name, bases):
		return OrderedDict()

	def __new__(self, name, bases, classdict):
		members = []
		keys = {}
		choices = OrderedDict()
		for key, value in classdict.items():
			if key.startswith("__"):
				continue
			members.append(key)
			if isinstance(value, tuple):
				value, alias = value
				keys[alias] = key
			else:
				alias = None
			keys[alias or key] = key
			choices[alias or key] = value

		for k, v in keys.items():
			classdict[v] = k

		classdict["__choices__"] = choices
		classdict["__members__"] = members

		# Note: Differences between Python 2.x and Python 3.x force us to
		# explicitly use unicode here, and to explicitly sort the list. In
		# Python 2.x, class members are unordered and so the ordering will
		# vary on different systems based on internal hashing. Without this
		# Django will continually require new no-op migrations.
		classdict["choices"] = tuple(
			(str(k), str(v)) for k, v in sorted(choices.items(), key=operator.itemgetter(0))
		)

		return type.__new__(self, name, bases, classdict)


class Enum(metaclass=EnumMetaClass):
	pass


class ApiErrorCode(Enum):
	"""
	Charge failure error codes.

	https://stripe.com/docs/error-codes
	"""

	account_already_exists = _("Account already exists")
	account_country_invalid_address = _("Account country invalid address")
	account_invalid = _("Account invalid")
	account_number_invalid = _("Account number invalid")
	alipay_upgrade_required = _("Alipay upgrade required")
	amount_too_large = _("Amount too large")
	amount_too_small = _("Amount too small")
	api_key_expired = _("Api key expired")
	balance_insufficient = _("Balance insufficient")
	bank_account_exists = _("Bank account exists")
	bank_account_unusable = _("Bank account unusable")
	bank_account_unverified = _("Bank account unverified")
	bitcoin_upgrade_required = _("Bitcoin upgrade required")
	card_declined = _("Card was declined")
	charge_already_captured = _("Charge already captured")
	charge_already_refunded = _("Charge already refunded")
	charge_disputed = _("Charge disputed")
	charge_exceeds_source_limit = _("Charge exceeds source limit")
	charge_expired_for_capture = _("Charge expired for capture")
	country_unsupported = _("Country unsupported")
	coupon_expired = _("Coupon expired")
	customer_max_subscriptions = _("Customer max subscriptions")
	email_invalid = _("Email invalid")
	expired_card = _("Expired card")
	idempotency_key_in_use = _("Idempotency key in use")
	incorrect_address = _("Incorrect address")
	incorrect_cvc = _("Incorrect security code")
	incorrect_number = _("Incorrect number")
	incorrect_zip = _("ZIP code failed validation")
	instant_payouts_unsupported = _("Instant payouts unsupported")
	invalid_card_type = _("Invalid card type")
	invalid_charge_amount = _("Invalid charge amount")
	invalid_cvc = _("Invalid security code")
	invalid_expiry_month = _("Invalid expiration month")
	invalid_expiry_year = _("Invalid expiration year")
	invalid_number = _("Invalid number")
	invalid_source_usage = _("Invalid source usage")
	invoice_no_customer_line_items = _("Invoice no customer line items")
	invoice_no_subscription_line_items = _("Invoice no subscription line items")
	invoice_not_editable = _("Invoice not editable")
	invoice_upcoming_none = _("Invoice upcoming none")
	livemode_mismatch = _("Livemode mismatch")
	missing = _("No card being charged")
	not_allowed_on_standard_account = _("Not allowed on standard account")
	order_creation_failed = _("Order creation failed")
	order_required_settings = _("Order required settings")
	order_status_invalid = _("Order status invalid")
	order_upstream_timeout = _("Order upstream timeout")
	out_of_inventory = _("Out of inventory")
	parameter_invalid_empty = _("Parameter invalid empty")
	parameter_invalid_integer = _("Parameter invalid integer")
	parameter_invalid_string_blank = _("Parameter invalid string blank")
	parameter_invalid_string_empty = _("Parameter invalid string empty")
	parameter_missing = _("Parameter missing")
	parameter_unknown = _("Parameter unknown")
	parameters_exclusive = _("Parameters exclusive")
	payment_intent_authentication_failure = _("Payment intent authentication failure")
	payment_intent_incompatible_payment_method = _(
		"Payment intent incompatible payment method"
	)
	payment_intent_invalid_parameter = _("Payment intent invalid parameter")
	payment_intent_payment_attempt_failed = _("Payment intent payment attempt failed")
	payment_intent_unexpected_state = _("Payment intent unexpected state")
	payment_method_unactivated = _("Payment method unactivated")
	payment_method_unexpected_state = _("Payment method unexpected state")
	payouts_not_allowed = _("Payouts not allowed")
	platform_api_key_expired = _("Platform api key expired")
	postal_code_invalid = _("Postal code invalid")
	processing_error = _("Processing error")
	product_inactive = _("Product inactive")
	rate_limit = _("Rate limit")
	resource_already_exists = _("Resource already exists")
	resource_missing = _("Resource missing")
	routing_number_invalid = _("Routing number invalid")
	secret_key_required = _("Secret key required")
	sepa_unsupported_account = _("SEPA unsupported account")
	shipping_calculation_failed = _("Shipping calculation failed")
	sku_inactive = _("SKU inactive")
	state_unsupported = _("State unsupported")
	tax_id_invalid = _("Tax id invalid")
	taxes_calculation_failed = _("Taxes calculation failed")
	testmode_charges_only = _("Testmode charges only")
	tls_version_unsupported = _("TLS version unsupported")
	token_already_used = _("Token already used")
	token_in_use = _("Token in use")
	transfers_not_allowed = _("Transfers not allowed")
	upstream_order_creation_failed = _("Upstream order creation failed")
	url_invalid = _("URL invalid")

	# deprecated
	invalid_swipe_data = _("Invalid swipe data")


class AccountType(Enum):
	standard = _("Standard")
	express = _("Express")
	custom = _("Custom")


class BalanceTransactionStatus(Enum):
	available = _("Available")
	pending = _("Pending")


class BalanceTransactionType(Enum):
	adjustment = _("Adjustment")
	application_fee = _("Application fee")
	application_fee_refund = _("Application fee refund")
	charge = _("Charge")
	network_cost = _("Network cost")
	payment = _("Payment")
	payment_failure_refund = _("Payment failure refund")
	payment_refund = _("Payment refund")
	payout = _("Payout")
	payout_cancel = _("Payout cancellation")
	payout_failure = _("Payout failure")
	refund = _("Refund")
	stripe_fee = _("Stripe fee")
	transfer = _("Transfer")
	transfer_refund = _("Transfer refund")
	validation = _("Validation")


class BankAccountHolderType(Enum):
	individual = _("Individual")
	company = _("Company")


class BankAccountStatus(Enum):
	new = _("New")
	validated = _("Validated")
	verified = _("Verified")
	verification_failed = _("Verification failed")
	errored = _("Errored")


class BusinessType(Enum):
	individual = _("Individual")
	company = _("Company")


class CardCheckResult(Enum):
	pass_ = (_("Pass"), "pass")
	fail = _("Fail")
	unavailable = _("Unavailable")
	unchecked = _("Unchecked")


class CardBrand(Enum):
	AmericanExpress = (_("American Express"), "American Express")
	DinersClub = (_("Diners Club"), "Diners Club")
	Discover = _("Discover")
	JCB = _("JCB")
	MasterCard = _("MasterCard")
	UnionPay = _("UnionPay")
	Visa = _("Visa")
	Unknown = _("Unknown")


class CardFundingType(Enum):
	credit = _("Credit")
	debit = _("Debit")
	prepaid = _("Prepaid")
	unknown = _("Unknown")


class CardTokenizationMethod(Enum):
	apple_pay = _("Apple Pay")
	android_pay = _("Android Pay")


class ChargeStatus(Enum):
	succeeded = _("Succeeded")
	pending = _("Pending")
	failed = _("Failed")


class CouponDuration(Enum):
	once = _("Once")
	repeating = _("Multi-month")
	forever = _("Forever")


class DisputeReason(Enum):
	duplicate = _("Duplicate")
	fraudulent = _("Fraudulent")
	subscription_canceled = _("Subscription canceled")
	product_unacceptable = _("Product unacceptable")
	product_not_received = _("Product not received")
	unrecognized = _("Unrecognized")
	credit_not_processed = _("Credit not processed")
	general = _("General")
	incorrect_account_details = _("Incorrect account details")
	insufficient_funds = _("Insufficient funds")
	bank_cannot_process = _("Bank cannot process")
	debit_not_authorized = _("Debit not authorized")
	customer_initiated = _("Customer-initiated")


class DisputeStatus(Enum):
	warning_needs_response = _("Warning needs response")
	warning_under_review = _("Warning under review")
	warning_closed = _("Warning closed")
	needs_response = _("Needs response")
	under_review = _("Under review")
	charge_refunded = _("Charge refunded")
	won = _("Won")
	lost = _("Lost")


class FileUploadPurpose(Enum):
	dispute_evidence = _("Dispute evidence")
	identity_document = _("Identity document")
	tax_document_user_upload = _("Tax document user upload")


class FileUploadType(Enum):
	pdf = _("PDF")
	jpg = _("JPG")
	png = _("PNG")
	csv = _("CSV")
	xls = _("XLS")
	xlsx = _("XLSX")
	docx = _("DOCX")


class InvoiceBilling(Enum):
	charge_automatically = _("Charge automatically")
	send_invoice = _("Send invoice")


class PayoutFailureCode(Enum):
	"""
	Payout failure error codes.

	https://stripe.com/docs/api#payout_failures
	"""

	account_closed = _("Bank account has been closed.")
	account_frozen = _("Bank account has been frozen.")
	bank_account_restricted = _("Bank account has restrictions on payouts allowed.")
	bank_ownership_changed = _("Destination bank account has changed ownership.")
	could_not_process = _("Bank could not process payout.")
	debit_not_authorized = _("Debit transactions not approved on the bank account.")
	insufficient_funds = _("Stripe account has insufficient funds.")
	invalid_account_number = _("Invalid account number")
	invalid_currency = _("Bank account does not support currency.")
	no_account = _("Bank account could not be located.")
	unsupported_card = _("Card no longer supported.")


class PayoutMethod(Enum):
	standard = _("Standard")
	instant = _("Instant")


class PayoutStatus(Enum):
	paid = _("Paid")
	pending = _("Pending")
	in_transit = _("In transit")
	canceled = _("Canceled")
	failed = _("Failed")


class PayoutType(Enum):
	bank_account = _("Bank account")
	card = _("Card")


class PlanAggregateUsage(Enum):
	last_during_period = _("Last during period")
	last_ever = _("Last ever")
	max = _("Max")
	sum = _("Sum")


class PlanBillingScheme(Enum):
	per_unit = _("Per unit")
	tiered = _("Tiered")


class PlanInterval(Enum):
	day = _("Day")
	week = _("Week")
	month = _("Month")
	year = _("Year")


class PlanUsageType(Enum):
	metered = _("Metered")
	licensed = _("Licensed")


class PlanTiersMode(Enum):
	graduated = _("Graduated")
	volume = _("Volume-based")


class ProductType(Enum):
	good = _("Good")
	service = _("Service")


class ScheduledQueryRunStatus(Enum):
	canceled = _("Canceled")
	failed = _("Failed")
	timed_out = _("Timed out")


class SourceFlow(Enum):
	redirect = _("Redirect")
	receiver = _("Receiver")
	code_verification = _("Code verification")
	none = _("None")


class SourceStatus(Enum):
	canceled = _("Canceled")
	chargeable = _("Chargeable")
	consumed = _("Consumed")
	failed = _("Failed")
	pending = _("Pending")


class SourceType(Enum):
	ach_credit_transfer = _("ACH Credit Transfer")
	ach_debit = _("ACH Debit")
	alipay = _("Alipay")
	bancontact = _("Bancontact")
	bitcoin = _("Bitcoin")
	card = _("Card")
	card_present = _("Card present")
	eps = _("EPS")
	giropay = _("Giropay")
	ideal = _("iDEAL")
	p24 = _("P24")
	paper_check = _("Paper check")
	sepa_debit = _("SEPA Direct Debit")
	sepa_credit_transfer = _("SEPA credit transfer")
	sofort = _("SOFORT")
	three_d_secure = _("3D Secure")


class LegacySourceType(Enum):
	card = _("Card")
	bank_account = _("Bank account")
	bitcoin_receiver = _("Bitcoin receiver")
	alipay_account = _("Alipay account")


class RefundFailureReason(Enum):
	lost_or_stolen_card = _("Lost or stolen card")
	expired_or_canceled_card = _("Expired or canceled card")
	unknown = _("Unknown")


class RefundReason(Enum):
	duplicate = _("Duplicate charge")
	fraudulent = _("Fraudulent")
	requested_by_customer = _("Requested by customer")


class RefundStatus(Enum):
	pending = _("Pending")
	succeeded = _("Succeeded")
	failed = _("Failed")
	canceled = _("Canceled")


class SourceUsage(Enum):
	reusable = _("Reusable")
	single_use = _("Single-use")


class SourceCodeVerificationStatus(Enum):
	pending = _("Pending")
	succeeded = _("Succeeded")
	failed = _("Failed")


class SourceRedirectFailureReason(Enum):
	user_abort = _("User-aborted")
	declined = _("Declined")
	processing_error = _("Processing error")


class SourceRedirectStatus(Enum):
	pending = _("Pending")
	succeeded = _("Succeeded")
	not_required = _("Not required")
	failed = _("Failed")


class SubscriptionStatus(Enum):
	trialing = _("Trialing")
	active = _("Active")
	past_due = _("Past due")
	canceled = _("Canceled")
	unpaid = _("Unpaid")


class DjstripePaymentMethodType(Enum):
	"""
	A djstripe-specific enum for the DjStripePaymentMethod model.
	"""

	card = _("Card")
	bank_account = _("Bank account")
	source = _("Source")


# Alias (Deprecated, remove in 2.2.0)
PaymentMethodType = DjstripePaymentMethodType
