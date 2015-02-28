# -*- coding: utf-8 -*-
"""
Beging porting from django-stripe-payments
"""
from . import settings


def djstripe_settings(request):
    # TODO - needs tests
    return {
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
    }
