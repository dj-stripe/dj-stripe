import stripe

from .base import StripeModel


class EarlyFraudWarning(StripeModel):
    """
    An early fraud warning indicates that the card issuer has notified us that a charge may be fraudulent.

    Stripe documentation: https://docs.stripe.com/api/radar/early_fraud_warnings?lang=python
    """

    stripe_class = stripe.radar.EarlyFraudWarning

    # https://docs.stripe.com/api/radar/early_fraud_warnings
    @property
    def actionable(self) -> bool:
        return self.stripe_data["actionable"]

    # https://docs.stripe.com/api/radar/early_fraud_warnings/object#early_fraud_warning_object-fraud_type
    @property
    def fraud_type(self) -> str:
        return self.stripe_data["fraud_type"]


class Review(StripeModel):
    """
    Reviews can be used to supplement automated fraud detection with human expertise.
    Learn more about Radar and reviewing payments here
    https://docs.stripe.com/radar/reviews.

    Stripe documentation: https://docs.stripe.com/api/radar/reviews?lang=python
    """

    stripe_class = stripe.Review

    # https://docs.stripe.com/api/radar/reviews/object#review_object-open
    @property
    def open(self) -> bool:
        return self.stripe_data["open"]

    # https://docs.stripe.com/api/radar/reviews/object#review_object-reason
    @property
    def readon(self) -> str:
        return self.stripe_data["reason"]
