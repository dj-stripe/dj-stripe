"""
Utility functions related to the djstripe app.
"""

import datetime
import warnings
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db.models.query import QuerySet
from django.utils import timezone

ANONYMOUS_USER_ERROR_MSG = (
    "dj-stripe's payment checking mechanisms require the user "
    "be authenticated before use. Please use django.contrib.auth's "
    "login_required decorator or a LoginRequiredMixin. "
    "Please read the warning at "
    "http://dj-stripe.readthedocs.org/en/latest/usage.html#ongoing-subscriptions."
)


def subscriber_has_active_subscription(subscriber, price=None, plan=None):
    """
    Helper function to check if a subscriber has an active subscription.

    Throws TypeError if both price and plan are defined.

    Throws improperlyConfigured if the subscriber is an instance of AUTH_USER_MODEL
    and get_user_model().is_anonymous == True.

    Activate subscription rules (or):
        * customer has active subscription

    If the subscriber is an instance of AUTH_USER_MODEL, active subscription rules (or):
        * customer has active subscription
        * user.is_superuser
        * user.is_staff

    If price and plan are None and there exists only one subscription, this method will
    check if that subscription is active. Calling this method with no price, no plan and
    multiple subscriptions will throw an exception.

    :param subscriber: The subscriber for which to check for an active subscription.
    :type subscriber: dj-stripe subscriber
    :param price: The price for which to check for an active subscription.
    :type price: Price or string (price ID)
    :param plan: The plan for which to check for an active subscription.
    :type plan: Plan or string (plan ID)
    """

    warnings.warn(
        "The subscriber_has_active_subscription utility function, and "
        "SubscriptionPaymentMiddleware, will be removed in dj-stripe 2.5.0.",
        DeprecationWarning,
    )

    if price and plan:
        raise TypeError("price and plan arguments cannot both be defined.")
    price = price or plan

    try:
        if subscriber.is_anonymous:
            raise ImproperlyConfigured(ANONYMOUS_USER_ERROR_MSG)
    except AttributeError:
        pass

    if isinstance(subscriber, get_user_model()):
        if subscriber.is_superuser or subscriber.is_staff:
            return True
    from .models import Customer

    customer, created = Customer.get_or_create(subscriber)
    if created or not customer.has_active_subscription(price):
        return False
    return True


def get_supported_currency_choices(api_key):
    """
    Pull a stripe account's supported currencies and returns a choices tuple of those
    supported currencies.

    :param api_key: The api key associated with the account from which to pull data.
    :type api_key: str
    """
    import stripe

    stripe.api_key = api_key

    account = stripe.Account.retrieve()
    supported_payment_currencies = stripe.CountrySpec.retrieve(account["country"])[
        "supported_payment_currencies"
    ]

    return [(currency, currency.upper()) for currency in supported_payment_currencies]


def clear_expired_idempotency_keys():
    from .models import IdempotencyKey

    threshold = timezone.now() - datetime.timedelta(hours=24)
    IdempotencyKey.objects.filter(created__lt=threshold).delete()


def convert_tstamp(response) -> Optional[datetime.datetime]:
    """
    Convert a Stripe API timestamp response (unix epoch) to a native datetime.
    """
    if response is None:
        # Allow passing None to convert_tstamp()
        return response

    # Overrides the set timezone to UTC - I think...
    tz = timezone.utc if settings.USE_TZ else None

    return datetime.datetime.fromtimestamp(response, tz)


# TODO: Finish this.
CURRENCY_SIGILS = {"CAD": "$", "EUR": "€", "GBP": "£", "USD": "$"}


def get_friendly_currency_amount(amount, currency: str) -> str:
    currency = currency.upper()
    sigil = CURRENCY_SIGILS.get(currency, "")
    return "{sigil}{amount:.2f} {currency}".format(
        sigil=sigil, amount=amount, currency=currency
    )


class QuerySetMock(QuerySet):
    """
    A mocked QuerySet class that does not handle updates.
    Used by UpcomingInvoice.invoiceitems.
    """

    @classmethod
    def from_iterable(cls, model, iterable):
        instance = cls(model)
        instance._result_cache = list(iterable)
        instance._prefetch_done = True
        return instance

    def _clone(self):
        return self.__class__.from_iterable(self.model, self._result_cache)

    def update(self):
        return 0

    def delete(self):
        return 0
