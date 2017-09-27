# -*- coding: utf-8 -*-
"""
.. module:: djstripe.settings.

   :synopsis: dj-stripe settings

.. moduleauthor:: @kavdev, @pydanny, @lskillen, and @chrissmejia
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import stripe
from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import six
from django.utils.module_loading import import_string

from .checks import validate_stripe_api_version


DEFAULT_STRIPE_API_VERSION = "2017-06-05"


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


def _get_idempotency_key(object_type, action, livemode):
    from .models import IdempotencyKey
    action = "{}:{}".format(object_type, action)
    idempotency_key, _created = IdempotencyKey.objects.get_or_create(action=action, livemode=livemode)
    return str(idempotency_key.uuid)


get_idempotency_key = get_callback_function("DJSTRIPE_IDEMPOTENCY_KEY_CALLBACK", _get_idempotency_key)

USE_NATIVE_JSONFIELD = getattr(settings, "DJSTRIPE_USE_NATIVE_JSONFIELD", False)

PRORATION_POLICY = getattr(settings, 'DJSTRIPE_PRORATION_POLICY', False)
CANCELLATION_AT_PERIOD_END = not getattr(settings, 'DJSTRIPE_PRORATION_POLICY', False)

DJSTRIPE_WEBHOOK_URL = getattr(settings, "DJSTRIPE_WEBHOOK_URL", r"^webhook/$")

# Webhook event callbacks allow an application to take control of what happens
# when an event from Stripe is received.  One suggestion is to put the event
# onto a task queue (such as celery) for asynchronous processing.
WEBHOOK_EVENT_CALLBACK = get_callback_function("DJSTRIPE_WEBHOOK_EVENT_CALLBACK")


TEST_API_KEY = getattr(settings, "STRIPE_TEST_SECRET_KEY", "")
LIVE_API_KEY = getattr(settings, "STRIPE_LIVE_SECRET_KEY", "")

# Determines whether we are in live mode or test mode
STRIPE_LIVE_MODE = getattr(settings, "STRIPE_LIVE_MODE", False)

# Default secret key
if hasattr(settings, "STRIPE_SECRET_KEY"):
    STRIPE_SECRET_KEY = settings.STRIPE_SECRET_KEY
else:
    STRIPE_SECRET_KEY = LIVE_API_KEY if STRIPE_LIVE_MODE else TEST_API_KEY

# Default public key
if hasattr(settings, "STRIPE_PUBLIC_KEY"):
    STRIPE_PUBLIC_KEY = settings.STRIPE_PUBLIC_KEY
elif STRIPE_LIVE_MODE:
    STRIPE_PUBLIC_KEY = getattr(settings, "STRIPE_LIVE_PUBLIC_KEY", "")
else:
    STRIPE_PUBLIC_KEY = getattr(settings, "STRIPE_TEST_PUBLIC_KEY", "")


SUBSCRIPTION_REDIRECT = getattr(settings, "DJSTRIPE_SUBSCRIPTION_REDIRECT", "djstripe:subscribe")


ZERO_DECIMAL_CURRENCIES = set([
    "bif", "clp", "djf", "gnf", "jpy", "kmf", "krw", "mga", "pyg", "rwf",
    "vnd", "vuv", "xaf", "xof", "xpf",
])


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


def get_stripe_api_version():
    """Get the desired API version to use for Stripe requests."""
    version = getattr(settings, 'STRIPE_API_VERSION', stripe.api_version)
    return version or DEFAULT_STRIPE_API_VERSION


def set_stripe_api_version(version=None, validate=True):
    """
    Set the desired API version to use for Stripe requests.

    :param version: The version to set for the Stripe API.
    :type version: ``str``
    :param validate: If True validate the value for the specified version).
    :type validate: ``bool``
    """
    version = version or get_stripe_api_version()

    if validate:
        valid = validate_stripe_api_version(version)
        if not valid:
            raise ValueError("Bad stripe API version: {}".format(version))

    stripe.api_version = version
