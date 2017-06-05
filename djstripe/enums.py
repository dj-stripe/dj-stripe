from enum import Enum as _Enum
from django.utils.decorators import classproperty
from django.utils.translation import ugettext as _


class Enum(_Enum):
    @classproperty
    def choices(cls):
        return tuple((cls.keys.get(k, k), v.value) for k, v in cls.__members__.items())

    @classproperty
    def keys(cls):
        # Returns a mapping of key overrides.
        # This allows using syntactically-incorrect values as keys,
        # such as keywords ("pass") or spaces ("Diners Club").
        # This cannot be an attribute, otherwise it would show up as a choice.
        return {}


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


class CardCheckResult(Enum):
    pass_ = _("Pass")
    fail = _("Fail")
    unavailable = _("Unavailable")
    unchecked = _("Unchecked")

    @classproperty
    def keys(cls):
        return {"pass_": "pass"}


class CardBrand(Enum):
    Visa = _("Visa")
    AmericanExpress = _("American Express")
    MasterCard = _("MasterCard")
    Discover = _("Discover")
    JCB = _("JCB")
    DinersClub = _("Diners Club")
    Unknown = _("Unknown")

    @classproperty
    def keys(cls):
        return {
            "AmericanExpress": "American Express",
            "DinersClub": "Diners Club",
        }


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


class PlanInterval(Enum):
    day = _("Day")
    week = _("Week")
    month = _("Month")
    year = _("Year")


class SourceType(Enum):
    card = _("Card")
    bank_account = _("Bank account")
    bitcoin_receiver = _("Bitcoin receiver")
    alipay_account = _("Alipay account")
