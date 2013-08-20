from __future__ import unicode_literals

from django.conf import settings

STRIPE_PUBLIC_KEY = settings.STRIPE_PUBLIC_KEY
INVOICE_FROM_EMAIL = getattr(
    settings,
    "DJSTRIPE_INVOICE_FROM_EMAIL",
    "billing@example.com"
)
PAYMENTS_PLANS = getattr(settings, "DJSTRIPE_PLANS", {})
PLAN_CHOICES = [
    (plan, PAYMENTS_PLANS[plan].get("name", plan))
    for plan in PAYMENTS_PLANS
]
