# -*- coding: utf-8 -*-
import warnings

from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from .models import Customer


ANONYMOUS_USER_ERROR_MSG = (
    "The subscription_payment_required decorator requires the user"
    "be authenticated before use. Please use django.contrib.auth's"
    "login_required decorator."
    "Please read the warning at"
    "http://dj-stripe.readthedocs.org/en/latest/usage.html#ongoing-subscriptions"
)


def user_has_active_subscription(user):
    warnings.warn("Deprecated - Use ``subscriber_has_active_subscription`` instead. This method will be removed in dj-stripe 1.0.", DeprecationWarning)
    return subscriber_has_active_subscription(user)


def subscriber_has_active_subscription(subscriber):
    """
    Helper function to check if a subscriber has an active subscription.
    Throws improperlyConfigured if the subscriber is an instance of AUTH_USER_MODEL
    and get_user_model().is_anonymous == True.

    Activate subscription rules (or):
        * customer has active subscription

    If the subscriber is an instance of AUTH_USER_MODEL, active subscription rules (or):
        * customer has active subscription
        * user.is_superuser
        * user.is_staff
    """

    if isinstance(subscriber, AnonymousUser):
        raise ImproperlyConfigured(ANONYMOUS_USER_ERROR_MSG)

    if isinstance(subscriber, get_user_model()):
        if subscriber.is_superuser or subscriber.is_staff:
            return True

    customer, created = Customer.get_or_create(subscriber)
    if created or not customer.has_active_subscription():
        return False
    return True


def get_supported_currency_choices(api_key):
    """
    Pulls a stripe account's supported currencies and returns a choices tuple of
    those supported currencies.

    :param api_key: The api key associated with the account from which to pull data.
    :type api_key: str
    """

    import stripe
    stripe.api_key = api_key

    account = stripe.Account.retrieve()
    return [(currency, currency.upper()) for currency in account["currencies_supported"]]
