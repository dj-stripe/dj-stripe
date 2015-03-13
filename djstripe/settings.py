# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib

from . import safe_settings

PY3 = sys.version > "3"

if PY3:
    basestring = str

subscriber_request_callback = getattr(settings, "DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK", (lambda request: request.user))


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

    # Attempt a Django 1.7 app lookup first
    try:
        from django.apps import apps as django_apps
    except ImportError:
        # Attempt to pull the model Django 1.5/1.6 style
        try:
            app_label, model_name = SUBSCRIBER_MODEL.split('.')
        except ValueError:
            raise ImproperlyConfigured("DJSTRIPE_SUBSCRIBER_MODEL must be of the form 'app_label.model_name'.")

        from django.db.models import get_model
        subscriber_model = get_model(app_label, model_name)
        if subscriber_model is None:
            raise ImproperlyConfigured("DJSTRIPE_SUBSCRIBER_MODEL refers to model '{model}' that has not been installed.".format(model=SUBSCRIBER_MODEL))
    else:
        # Continue attempting to pull the model Django 1.7 style
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


def plan_from_stripe_id(stripe_id):
    for key in PAYMENTS_PLANS.keys():
        if PAYMENTS_PLANS[key].get("stripe_plan_id") == stripe_id:
            return key


def load_path_attr(path):
    i = path.rfind(".")
    module, attr = path[:i], path[i + 1:]
    try:
        mod = importlib.import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured("Error importing %s: '%s'" % (module, e))
    try:
        attr = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured("Module '%s' does not define a '%s'" % (
            module, attr)
        )
    return attr


STRIPE_PUBLIC_KEY = safe_settings.STRIPE_PUBLIC_KEY
INVOICE_FROM_EMAIL = safe_settings.INVOICE_FROM_EMAIL
PAYMENTS_PLANS = safe_settings.PAYMENTS_PLANS
PLAN_CHOICES = safe_settings.PLAN_CHOICES
PASSWORD_INPUT_RENDER_VALUE = safe_settings.PASSWORD_INPUT_RENDER_VALUE
PASSWORD_MIN_LENGTH = safe_settings.PASSWORD_MIN_LENGTH

PRORATION_POLICY = safe_settings.PRORATION_POLICY
PRORATION_POLICY_FOR_UPGRADES = safe_settings.PRORATION_POLICY_FOR_UPGRADES
CANCELLATION_AT_PERIOD_END = safe_settings.CANCELLATION_AT_PERIOD_END

SEND_INVOICE_RECEIPT_EMAILS = safe_settings.SEND_INVOICE_RECEIPT_EMAILS


DEFAULT_PLAN = getattr(
    settings,
    "DJSTRIPE_DEFAULT_PLAN",
    None
)

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

if isinstance(trial_period_for_subscriber_callback, basestring):
    trial_period_for_subscriber_callback = load_path_attr(
        trial_period_for_subscriber_callback
    )

DJSTRIPE_WEBHOOK_URL = getattr(
    settings,
    "DJSTRIPE_WEBHOOK_URL",
    r"^webhook/$"
)
