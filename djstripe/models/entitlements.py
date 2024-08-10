import stripe

from .base import StripeModel


class Feature(StripeModel):
    stripe_class = stripe.entitlements.Feature


class ActiveEntitlement(StripeModel):
    stripe_class = stripe.entitlements.ActiveEntitlement
