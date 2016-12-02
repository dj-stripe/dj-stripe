# -*- coding: utf-8 -*-
"""
.. module:: djstripe.utils.

  :synopsis: dj-stripe - Utility functions related to the djstripe app.

.. moduleauthor:: @kavdev, @pydanny, @wahuneke
"""
import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone


ANONYMOUS_USER_ERROR_MSG = (
    "dj-stripe's payment checking mechanisms require the user "
    "be authenticated before use. Please use django.contrib.auth's "
    "login_required decorator or a LoginRequiredMixin. "
    "Please read the warning at "
    "http://dj-stripe.readthedocs.org/en/latest/usage.html#ongoing-subscriptions."
)


def subscriber_has_active_subscription(subscriber, plan=None):
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

    :param subscriber: The subscriber for which to check for an active subscription.
    :type subscriber: dj-stripe subscriber
    :param plan: The plan for which to check for an active subscription. If plan is None and
                 there exists only one subscription, this method will check if that subscription
                 is active. Calling this method with no plan and multiple subscriptions will throw
                 an exception.
    :type plan: Plan or string (plan ID)

    """
    if isinstance(subscriber, AnonymousUser):
        raise ImproperlyConfigured(ANONYMOUS_USER_ERROR_MSG)

    if isinstance(subscriber, get_user_model()):
        if subscriber.is_superuser or subscriber.is_staff:
            return True
    from .models import Customer

    customer, created = Customer.get_or_create(subscriber)
    if created or not customer.has_active_subscription(plan):
        return False
    return True


def get_supported_currency_choices(api_key):
    """
    Pull a stripe account's supported currencies and returns a choices tuple of those supported currencies.

    :param api_key: The api key associated with the account from which to pull data.
    :type api_key: str
    """
    import stripe
    stripe.api_key = api_key

    account = stripe.Account.retrieve()
    supported_payment_currencies = stripe.CountrySpec.retrieve(account["country"])["supported_payment_currencies"]

    return [(currency, currency.upper()) for currency in supported_payment_currencies]


def dict_nested_accessor(d, name):
    """
    Access a dictionary value, possibly in a nested dictionary.

    >>> dict_nested_accessor({'id': 'joe'}, 'id')
    "joe"
    >>> dict_nested_accessor({'inner': {'id': 'joe'}}, 'inner.id')
    "joe"

    :type d: dict
    """
    names = name.split(".", 1)
    if len(names) > 1:
        return dict_nested_accessor(d[names[0]], names[1])
    else:
        return d[name]


def convert_tstamp(response, field_name=None):
    """
    Convert a Stripe API timestamp response (unix epoch) to a native datetime.

    :rtype: datetime
    """
    # Overrides the set timezone to UTC - I think...
    tz = timezone.utc if settings.USE_TZ else None

    if not field_name:
        return datetime.datetime.fromtimestamp(response, tz)
    else:
        if field_name in response and response[field_name]:
            return datetime.datetime.fromtimestamp(response[field_name], tz)
