"""
Beging porting from django-stripe-payments
"""
from __future__ import unicode_literals
import sys
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib

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

User = get_user_model()


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
PLAN_LIST = []
for p in PAYMENTS_PLANS:
    if PAYMENTS_PLANS[p].get("stripe_plan_id"):
        plan = PAYMENTS_PLANS[p]
        plan['plan'] = p
        PLAN_LIST.append(plan)

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