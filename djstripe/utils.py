# -*- coding: utf-8 -*-

import warnings

from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from .models import DJStripeCustomer


ANONYMOUS_USER_ERROR_MSG = (
    "The subscription_payment_required decorator requires the user"
    "be authenticated before use. Please use django.contrib.auth's"
    "login_required decorator."
    "Please read the warning at"
    "http://dj-stripe.readthedocs.org/en/latest/usage.html#ongoing-subscriptions"
)


def user_has_active_subscription(user):
    warnings.warn("Deprecated - Use ``customer_has_active_subscription`` instead. This method will be removed in dj-stripe 1.0.", DeprecationWarning)
    return customer_has_active_subscription(user)


def customer_has_active_subscription(customer):
    """
    Helper function to check if a customer has an active subscription.
    Throws improperlyConfigured if the customer is an instance of AUTH_USER_MODEL
    and get_user_model().is_anonymous == True.

    Activate subscription rules (or):
        * djstripecustomer has active subscription

    If the customer is an instance of AUTH_USER_MODEL, active subscription rules (or):
        * djstripecustomer has active subscription
        * user.is_superuser
        * user.is_staff
    """

    if isinstance(customer, AnonymousUser):
        raise ImproperlyConfigured(ANONYMOUS_USER_ERROR_MSG)

    if isinstance(customer, get_user_model()):
        if customer.is_superuser or customer.is_staff:
            return True

    djstripecustomer, created = DJStripeCustomer.get_or_create(customer)
    if created or not djstripecustomer.has_active_subscription():
        return False
    return True
