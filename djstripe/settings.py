# -*- coding: utf-8 -*-
"""
.. module:: djstripe.settings.

   :synopsis: dj-stripe settings

.. moduleauthor:: @kavdev, @pydanny, @lskillen, and @chrissmejia
"""
from __future__ import unicode_literals

import sys

from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.module_loading import import_string

PY3 = sys.version > "3"


def get_callback_function(setting_name, default=None):
    """
    Resolve a callback function based on a setting name.

    If the setting value isn't set, default is returned.  If the setting value
    is already a callable function, that value is used - If the setting value
    is a string, an attempt is made to import it.  Anything else will result in
    a failed import causing ImportError to be raised.

    :param setting_name: The name of the setting to resolve a callback from.
    :type setting_name: string (``str``/``unicode``)
    :param default: The default to return if setting isn't populated.
    :type default: ``bool``
    :returns: The resolved callback function (if any).
    :type: ``callable``
    """
    func = getattr(settings, setting_name, None)
    if not func:
        return default

    if callable(func):
        return func

    if isinstance(func, six.string_types):
        func = import_string(func)

    if not callable(func):
        raise ImproperlyConfigured("{name} must be callable.".format(name=setting_name))

    return func


subscriber_request_callback = get_callback_function("DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK",
                                                    default=(lambda request: request.user))

INVOICE_FROM_EMAIL = getattr(settings, "DJSTRIPE_INVOICE_FROM_EMAIL", "billing@example.com")
PAYMENTS_PLANS = getattr(settings, "DJSTRIPE_PLANS", {})
PLAN_HIERARCHY = getattr(settings, "DJSTRIPE_PLAN_HIERARCHY", {})

PASSWORD_INPUT_RENDER_VALUE = getattr(settings, 'DJSTRIPE_PASSWORD_INPUT_RENDER_VALUE', False)
PASSWORD_MIN_LENGTH = getattr(settings, 'DJSTRIPE_PASSWORD_MIN_LENGTH', 6)

PRORATION_POLICY = getattr(settings, 'DJSTRIPE_PRORATION_POLICY', False)
PRORATION_POLICY_FOR_UPGRADES = getattr(settings, 'DJSTRIPE_PRORATION_POLICY_FOR_UPGRADES', False)
CANCELLATION_AT_PERIOD_END = not getattr(settings, 'DJSTRIPE_PRORATION_POLICY', False)

SEND_INVOICE_RECEIPT_EMAILS = getattr(settings, "DJSTRIPE_SEND_INVOICE_RECEIPT_EMAILS", True)
CURRENCIES = getattr(settings, "DJSTRIPE_CURRENCIES", (
    ('usd', 'U.S. Dollars',),
    ('gbp', 'Pounds (GBP)',),
    ('eur', 'Euros',))
)

DEFAULT_PLAN = getattr(settings, "DJSTRIPE_DEFAULT_PLAN", None)

# Try to find the new settings variable first. If that fails, revert to the
# old variable.
trial_period_for_subscriber_callback = (
    get_callback_function("DJSTRIPE_TRIAL_PERIOD_FOR_SUBSCRIBER_CALLBACK") or
    get_callback_function("DJSTRIPE_TRIAL_PERIOD_FOR_USER_CALLBACK"))

DJSTRIPE_WEBHOOK_URL = getattr(settings, "DJSTRIPE_WEBHOOK_URL", r"^webhook/$")

# Webhook event callbacks allow an application to take control of what happens
# when an event from Stripe is received.  One suggestion is to put the event
# onto a task queue (such as celery) for asynchronous processing.
WEBHOOK_EVENT_CALLBACK = get_callback_function("DJSTRIPE_WEBHOOK_EVENT_CALLBACK")


def get_subscriber_model_string():
    """Get the configured subscriber model as a module path string."""
    return getattr(settings, "DJSTRIPE_SUBSCRIBER_MODEL", settings.AUTH_USER_MODEL)


def get_subscriber_model():
    """
    Attempt to pull settings.DJSTRIPE_SUBSCRIBER_MODEL.

    Users have the option of specifying a custom subscriber model via the
    DJSTRIPE_SUBSCRIBER_MODEL setting.

    This methods falls back to AUTH_USER_MODEL if DJSTRIPE_SUBSCRIBER_MODEL is not set.

    Returns the subscriber model that is active in this project.
    """
    model_name = get_subscriber_model_string()

    # Attempt a Django 1.7 app lookup
    try:
        subscriber_model = django_apps.get_model(model_name)
    except ValueError:
        raise ImproperlyConfigured("DJSTRIPE_SUBSCRIBER_MODEL must be of the form 'app_label.model_name'.")
    except LookupError:
        raise ImproperlyConfigured("DJSTRIPE_SUBSCRIBER_MODEL refers to model '{model}' "
                                   "that has not been installed.".format(model=model_name))

    if (("email" not in [field_.name for field_ in subscriber_model._meta.get_fields()]) and
            not hasattr(subscriber_model, 'email')):
        raise ImproperlyConfigured("DJSTRIPE_SUBSCRIBER_MODEL must have an email attribute.")

    if model_name != settings.AUTH_USER_MODEL:
        # Custom user model detected. Make sure the callback is configured.
        func = get_callback_function("DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK")
        if not func:
            raise ImproperlyConfigured(
                "DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK must be implemented "
                "if a DJSTRIPE_SUBSCRIBER_MODEL is defined.")

    return subscriber_model
