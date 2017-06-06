from collections import OrderedDict

from django.utils.translation import ugettext as _


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
        classdict["choices"] = tuple(choices.items())

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


class SubscriptionStatus(Enum):
    trialing = _("Trialing")
    active = _("Active")
    past_due = _("Past due")
    canceled = _("Canceled")
    unpaid = _("Unpaid")
