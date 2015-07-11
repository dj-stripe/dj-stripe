# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict
import sys

from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

PY3 = sys.version > "3"

subscriber_request_callback = getattr(settings, "DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK", (lambda request: request.user))

INVOICE_FROM_EMAIL = getattr(settings, "DJSTRIPE_INVOICE_FROM_EMAIL", "billing@example.com")
PAYMENTS_PLANS = getattr(settings, "DJSTRIPE_PLANS", {})
PLAN_HIERARCHY = getattr(settings, "DJSTRIPE_PLAN_HIERARCHY", {})

# Sort the PAYMENT_PLANS dictionary ascending by price.
PAYMENT_PLANS = OrderedDict(sorted(PAYMENTS_PLANS.items(), key=lambda t: t[1]['price']))
PLAN_CHOICES = [(plan, PAYMENTS_PLANS[plan].get("name", plan)) for plan in PAYMENTS_PLANS]

PASSWORD_INPUT_RENDER_VALUE = getattr(settings, 'DJSTRIPE_PASSWORD_INPUT_RENDER_VALUE', False)
PASSWORD_MIN_LENGTH = getattr(settings, 'DJSTRIPE_PASSWORD_MIN_LENGTH', 6)

PRORATION_POLICY = getattr(settings, 'DJSTRIPE_PRORATION_POLICY', False)
PRORATION_POLICY_FOR_UPGRADES = getattr(settings, 'DJSTRIPE_PRORATION_POLICY_FOR_UPGRADES', False)
CANCELLATION_AT_PERIOD_END = not getattr(settings, 'DJSTRIPE_PRORATION_POLICY', False)  # TODO - need to find a better way to do this

SEND_INVOICE_RECEIPT_EMAILS = getattr(settings, "DJSTRIPE_SEND_INVOICE_RECEIPT_EMAILS", True)
CURRENCIES = getattr(settings, "DJSTRIPE_CURRENCIES", (
    ('usd', 'U.S. Dollars',),
    ('gbp', 'Pounds (GBP)',),
    ('eur', 'Euros',))
)

DEFAULT_PLAN = getattr(settings, "DJSTRIPE_DEFAULT_PLAN", None)

PLAN_LIST = []
for p in PAYMENTS_PLANS:
    if PAYMENTS_PLANS[p].get("stripe_plan_id"):
        plan = PAYMENTS_PLANS[p]
        plan['plan'] = p
        PLAN_LIST.append(plan)

# Try to find the new settings variable first. If that fails, revert to the
# old variable.
trial_period_for_subscriber_callback = getattr(settings,
    "DJSTRIPE_TRIAL_PERIOD_FOR_SUBSCRIBER_CALLBACK",
    getattr(settings, "DJSTRIPE_TRIAL_PERIOD_FOR_USER_CALLBACK", None)
)

DJSTRIPE_WEBHOOK_URL = getattr(settings, "DJSTRIPE_WEBHOOK_URL", r"^webhook/$")


def plan_from_stripe_id(stripe_id):
    payment_plans = getattr(settings, "DJSTRIPE_PLANS", {})
    plan_id = None

    for key in payment_plans.keys():
        if payment_plans[key].get("stripe_plan_id") == stripe_id:
            plan_id = key

    return plan_id


def _check_subscriber_for_email_address(subscriber_model, message):
    """Ensure the custom model has an ``email`` field or property."""

    if ("email" not in subscriber_model._meta.get_all_field_names()) and not hasattr(subscriber_model, 'email'):
        raise ImproperlyConfigured(message)


def get_subscriber_model():
    """
    Users have the option of specifying a custom subscriber model via the
    DJSTRIPE_SUBSCRIBER_MODEL setting.

    This method attempts to pull that model from settings, and falls back to
    AUTH_USER_MODEL if DJSTRIPE_SUBSCRIBER_MODEL is not set.

    Note: Django 1.4 support was dropped in #107
          https://github.com/pydanny/dj-stripe/pull/107

    Returns the subscriber model that is active in this project.
    """

    SUBSCRIBER_MODEL = getattr(settings, "DJSTRIPE_SUBSCRIBER_MODEL", None)

    # Check if a subscriber model is specified. If not, fall back and exit.
    if not SUBSCRIBER_MODEL:
        from django.contrib.auth import get_user_model
        subscriber_model = get_user_model()
        _check_subscriber_for_email_address(subscriber_model, "The customer user model must have an email attribute.")

        return subscriber_model

    subscriber_model = None

    # Attempt a Django 1.7 app lookup
    try:
        subscriber_model = django_apps.get_model(SUBSCRIBER_MODEL)
    except ValueError:
        raise ImproperlyConfigured("DJSTRIPE_SUBSCRIBER_MODEL must be of the form 'app_label.model_name'.")
    except LookupError:
        raise ImproperlyConfigured("DJSTRIPE_SUBSCRIBER_MODEL refers to model '{model}' that has not been installed.".format(model=SUBSCRIBER_MODEL))

    _check_subscriber_for_email_address(subscriber_model, "DJSTRIPE_SUBSCRIBER_MODEL must have an email attribute.")

    # Custom user model detected. Make sure the callback is configured.
    if hasattr(settings, "DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK"):
        if not callable(getattr(settings, "DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK")):
            raise ImproperlyConfigured("DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK must be callable.")
    else:
        raise ImproperlyConfigured("DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK must be implemented if a DJSTRIPE_SUBSCRIBER_MODEL is defined.")

    return subscriber_model
