# -*- coding: utf-8 -*-
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
    Pulls a stripe account's supported currencies and returns a choices tuple of
    those supported currencies.

    :param api_key: The api key associated with the account from which to pull data.
    :type api_key: str
    """

    import stripe
    stripe.api_key = api_key

    account = stripe.Account.retrieve()
    return [(currency, currency.upper()) for currency in account["currencies_supported"]]


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
    Intended for use converting from a Stripe API timestamp resposne into a native date

    :rtype: datetime
    """
    # Overrides the set timezone to UTC - I think...
    tz = timezone.utc if settings.USE_TZ else None

    if not field_name:
        return datetime.datetime.fromtimestamp(response, tz)
    else:
        if field_name in response and response[field_name]:
            return datetime.datetime.fromtimestamp(response[field_name], tz)


def simple_stripe_pagination_iterator(stripe_object, **kwargs):
    """ A simple utility to iterate over parginated stripe object lists. Use this in place
        of a direct stripe_object.all().

        Note that ``limit``, ``starting_after``, and ``ending_before`` arguments to this function
        are reserved. If these arguments are passed, they will be discarded.

        See the Stripe API documentation for the stripe object to find out which filter kwargs are accepted.

        :param stripe_object: A stripe object that supports the all() method.
    """

    reserved_kwargs = ["limit", "starting_after", "ending_before"]

    # Discard any reserved kwargs that were passed in.
    for kwarg in reserved_kwargs:
        try:
            del kwargs[kwarg]
        except KeyError:
            continue

    stripe_object_list_response = stripe_object.all(limit=100, **kwargs)

    for list_object in stripe_object_list_response["data"]:
        yield list_object

    while stripe_object_list_response["has_more"]:
        stripe_object_list_response = stripe_object.all(limit=100, starting_after=stripe_object_list_response["data"][-1], **kwargs)

        for list_object in stripe_object_list_response["data"]:
            yield list_object
