from __future__ import unicode_literals
from collections import OrderedDict

from django.conf import settings

STRIPE_PUBLIC_KEY = settings.STRIPE_PUBLIC_KEY
INVOICE_FROM_EMAIL = getattr(
    settings,
    "DJSTRIPE_INVOICE_FROM_EMAIL",
    "billing@example.com"
)

# Get the PAYMENTS_PLANS dictionary
PAYMENTS_PLANS = getattr(settings, "DJSTRIPE_PLANS", {})

# Sort the PAYMENT_PLANS dictionary ascending by price.
PAYMENT_PLANS = OrderedDict(sorted(PAYMENTS_PLANS.items(), key=lambda t: t[1]['price']))

PLAN_CHOICES = [
    (plan, PAYMENTS_PLANS[plan].get("name", plan))
    for plan in PAYMENTS_PLANS
]

PASSWORD_INPUT_RENDER_VALUE = getattr(
    settings, 'DJSTRIPE_PASSWORD_INPUT_RENDER_VALUE', False)
PASSWORD_MIN_LENGTH = getattr(
    settings, 'DJSTRIPE_PASSWORD_MIN_LENGTH', 6)
