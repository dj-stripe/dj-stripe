"""
Beging porting from django-stripe-payments
"""
from __future__ import unicode_literals
import sys
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import importlib

PY3 = sys.version > "3"

try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
except ImportError:
    from django.contrib.auth.models import User


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


STRIPE_PUBLIC_KEY = settings.STRIPE_PUBLIC_KEY
INVOICE_FROM_EMAIL = getattr(
    settings,
    "PAYMENTS_INVOICE_FROM_EMAIL",
    "billing@example.com"
)
PAYMENTS_PLANS = getattr(settings, "PAYMENTS_PLANS", {})
PLAN_CHOICES = [
    (plan, PAYMENTS_PLANS[plan].get("name", plan))
    for plan in PAYMENTS_PLANS
]
DEFAULT_PLAN = getattr(
    settings,
    "PAYMENTS_DEFAULT_PLAN",
    None
)
TRIAL_PERIOD_FOR_USER_CALLBACK = getattr(
    settings,
    "PAYMENTS_TRIAL_PERIOD_FOR_USER_CALLBACK",
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