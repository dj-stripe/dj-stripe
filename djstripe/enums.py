import operator
from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _


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
            (str(k), str(v))
            for k, v in sorted(choices.items(), key=operator.itemgetter(0))
        )

        return type.__new__(self, name, bases, classdict)


class Enum(metaclass=EnumMetaClass):
    pass


class ApiErrorCode(Enum):
    """
    Charge failure error codes.

    https://stripe.com/docs/api#error-codes
    """

    invalid_number = _("Invalid number")
    invalid_expiry_month = _("Invalid expiration month")
    invalid_expiry_year = _("Invalid expiration year")
    invalid_cvc = _("Invalid security code")
    invalid_swipe_data = _("Invalid swipe data")
    incorrect_number = _("Incorrect number")
    expired_card = _("Expired card")
    incorrect_cvc = _("Incorrect security code")
    incorrect_zip = _("ZIP code failed validation")
    card_declined = _("Card was declined")
    missing = _("No card being charged")
    processing_error = _("Processing error")


class AccountType(Enum):
    standard = _("Standard")
    express = _("Express")
    custom = _("Custom")


class BankAccountHolderType(Enum):
    individual = _("Individual")
    company = _("Company")


class BankAccountStatus(Enum):
    new = _("New")
    validated = _("Validated")
    verified = _("Verified")
    verification_failed = _("Verification failed")
    errored = _("Errored")


class CardCheckResult(Enum):
    pass_ = (_("Pass"), "pass")
    fail = _("Fail")
    unavailable = _("Unavailable")
    unchecked = _("Unchecked")


class CardBrand(Enum):
    Visa = _("Visa")
    AmericanExpress = (_("American Express"), "American Express")
    MasterCard = _("MasterCard")
    Discover = _("Discover")
    JCB = _("JCB")
    DinersClub = (_("Diners Club"), "Diners Club")
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
    card = _("Card")
    three_d_secure = _("3D Secure")
    alipay = _("Alipay")
    ach_credit_transfer = _("ACH Credit Transfer")
    bancontact = _("Bancontact")
    bitcoin = _("Bitcoin")
    giropay = _("Giropay")
    ideal = _("iDEAL")
    p24 = _("P24")
    sepa_debit = _("SEPA Direct Debit")
    sofort = _("SOFORT")


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


class PaymentMethodType(Enum):
    """
    A djstripe-specific enum for the PaymentMethod model.
    """
    card = _("Card")
    bank_account = _("Bank account")
    source = _("Source")
