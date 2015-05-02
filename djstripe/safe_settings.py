# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings

STRIPE_PUBLIC_KEY = settings.STRIPE_PUBLIC_KEY
INVOICE_FROM_EMAIL = getattr(
    settings,
    "DJSTRIPE_INVOICE_FROM_EMAIL",
    "billing@example.com"
)

PASSWORD_INPUT_RENDER_VALUE = getattr(
    settings, 'DJSTRIPE_PASSWORD_INPUT_RENDER_VALUE', False)
PASSWORD_MIN_LENGTH = getattr(
    settings, 'DJSTRIPE_PASSWORD_MIN_LENGTH', 6)


PRORATION_POLICY = getattr(
    settings, 'DJSTRIPE_PRORATION_POLICY', False)

PRORATION_POLICY_FOR_UPGRADES = getattr(
    settings, 'DJSTRIPE_PRORATION_POLICY_FOR_UPGRADES', False)

# TODO - need to find a better way to do this
CANCELLATION_AT_PERIOD_END = not PRORATION_POLICY

# Manages sending of receipt emails
SEND_INVOICE_RECEIPT_EMAILS = getattr(settings, "DJSTRIPE_SEND_INVOICE_RECEIPT_EMAILS", True)

CURRENCIES = getattr(
    settings, "DJSTRIPE_CURRENCIES", (
        ('usd', 'U.S. Dollars',),
        ('gbp', 'Pounds (GBP)',),
        ('eur', 'Euros',)))
