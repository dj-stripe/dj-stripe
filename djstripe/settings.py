# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib
from django.utils.functional import SimpleLazyObject

from . import safe_settings

PY3 = sys.version > "3"


def get_user_model():
    """ Place this in a function to avoid circular imports """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
    except ImportError:
        from django.contrib.auth.models import User
    return User

User = SimpleLazyObject(get_user_model)


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
TRIAL_PERIOD_FOR_USER_CALLBACK = getattr(
    settings,
    "DJSTRIPE_TRIAL_PERIOD_FOR_USER_CALLBACK",
    None
)

if PY3:
    if isinstance(TRIAL_PERIOD_FOR_USER_CALLBACK, str):
        TRIAL_PERIOD_FOR_USER_CALLBACK = load_path_attr(
            TRIAL_PERIOD_FOR_USER_CALLBACK
        )
else:
    if isinstance(TRIAL_PERIOD_FOR_USER_CALLBACK, basestring):
        TRIAL_PERIOD_FOR_USER_CALLBACK = load_path_attr(
            TRIAL_PERIOD_FOR_USER_CALLBACK
        )

DJSTRIPE_WEBHOOK_URL = getattr(
    settings,
    "DJSTRIPE_WEBHOOK_URL",
    r"^webhook/$"
)
