"""
Beging porting from django-stripe-payments
"""
from . import settings


def djstripe_settings(request):
    # TODO - needs tests
    return {
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
        "PLAN_CHOICES": settings.PLAN_CHOICES,
        "PLAN_LIST": settings.PLAN_LIST,
        "PAYMENT_PLANS": settings.PAYMENTS_PLANS  # possibly nuke
    }
