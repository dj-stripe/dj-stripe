import stripe

from .base import StripeModel


class EarlyFraudWarning(StripeModel):
    stripe_class = stripe.radar.EarlyFraudWarning


class Review(StripeModel):
    stripe_class = stripe.Review
