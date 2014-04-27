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
PASSWORD_INPUT_RENDER_VALUE = getattr(
    settings, 'DJSTRIPE_PASSWORD_INPUT_RENDER_VALUE', False)
PASSWORD_MIN_LENGTH = getattr(
    settings, 'DJSTRIPE_PASSWORD_MIN_LENGTH', 6)
DJSTRIPE_CUSTOMER_RELATED_MODEL_PLUGIN = getattr(settings, "DJSTRIPE_CUSTOMER_RELATED_MODEL_PLUGIN", "djstripe.plugins.default.DefaultPlugin")
DJSTRIPE_RELATED_MODEL_NAME_FIELD = getattr(settings, "DJSTRIPE_RELATED_MODEL_NAME_FIELD", "username")
DJSTRIPE_RELATED_MODEL_BILLING_EMAIL_FIELD = getattr(settings, "DJSTRIPE_RELATED_MODEL_BILLING_EMAIL_FIELD", "email")