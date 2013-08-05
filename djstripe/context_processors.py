"""
Beging porting from django-stripe-payments
"""
from payments import settings


def payments_settings(request):
    return {
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
        "PLAN_CHOICES": settings.PLAN_CHOICES,
        "PAYMENT_PLANS": settings.PAYMENTS_PLANS
    }
