from __future__ import absolute_import, division, print_function, unicode_literals
from collections import OrderedDict
import operator

from django.utils.translation import ugettext as _
from django.utils.six import add_metaclass, text_type


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
            (text_type(k), text_type(v))
            for k, v in sorted(choices.items(), key=operator.itemgetter(0))
        )

        return type.__new__(self, name, bases, classdict)


@add_metaclass(EnumMetaClass)
class Enum(object):
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
