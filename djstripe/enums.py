from django.utils.translation import ugettext as _
from djchoices import C, DjangoChoices


class ApiErrorCode(DjangoChoices):
    """
    Charge failure error codes.

    https://stripe.com/docs/api#error-codes
    """

    invalid_number = C(_("Invalid number"), "invalid_number")
    invalid_expiry_month = C(_("Invalid expiration month"), "invalid_expiry_month")
    invalid_expiry_year = C(_("Invalid expiration year"), "invalid_expiry_year")
    invalid_cvc = C(_("Invalid security code"), "invalid_cvc")
    invalid_swipe_data = C(_("Invalid swipe data"), "invalid_swipe_data")
    incorrect_number = C(_("Incorrect number"), "incorrect_number")
    expired_card = C(_("Expired card"), "expired_card")
    incorrect_cvc = C(_("Incorrect security code"), "incorrect_cvc")
    incorrect_zip = C(_("ZIP code failed validation"), "incorrect_zip")
    card_declined = C(_("Card was declined"), "card_declined")
    missing = C(_("No card being charged"), "missing")
    processing_error = C(_("Processing error"), "processing_error")


class CardCheckResult(DjangoChoices):
    pass_ = C(_("Pass"), "pass")
    fail = C(_("Fail"), "fail")
    unavailable = C(_("Unavailable"), "unavailable")
    unchecked = C(_("Unchecked"), "unchecked")


class CardBrand(DjangoChoices):
    Visa = C(_("Visa"), "Visa")
    AmericanExpress = C(_("American Express"), "American Express")
    MasterCard = C(_("MasterCard"), "MasterCard")
    Discover = C(_("Discover"), "Discover")
    JCB = C(_("JCB"), "JCB")
    DinersClub = C(_("Diners Club"), "Diners Club")
    Unknown = C(_("Unknown"), "Unknown")


class CardFundingType(DjangoChoices):
    credit = C(_("Credit"), "credit")
    debit = C(_("Debit"), "debit")
    prepaid = C(_("Prepaid"), "prepaid")
    unknown = C(_("Unknown"), "unknown")


class CardTokenizationMethod(DjangoChoices):
    apple_pay = C(_("Apple Pay"), "apple_pay")
    android_pay = C(_("Android Pay"), "android_pay")


class ChargeStatus(DjangoChoices):
    succeeded = C(_("Succeeded"), "succeeded")
    pending = C(_("Pending"), "pending")
    failed = C(_("Failed"), "failed")


class CouponDuration(DjangoChoices):
    once = C(_("Once"), "once")
    repeating = C(_("Multi-month"), "repeating")
    forever = C(_("Forever"), "forever")


class PlanInterval(DjangoChoices):
    day = C(_("Day"), "day")
    week = C(_("Week"), "week")
    month = C(_("Month"), "month")
    year = C(_("Year"), "year")


class SourceType(DjangoChoices):
    card = C(_("Card"), "card")
    bank_account = C(_("Bank account"), "bank_account")
    bitcoin_receiver = C(_("Bitcoin receiver"), "bitcoin_receiver")
    alipay_account = C(_("Alipay account"), "alipay_account")
