import stripe

from .base import StripeModel


class IssuingAuthorization(StripeModel):
    stripe_class = stripe.issuing.Authorization

    class Meta:
        db_table = "djstripe_issuing_authorization"


class IssuingCard(StripeModel):
    stripe_class = stripe.issuing.Card

    class Meta:
        db_table = "djstripe_issuing_card"


class IssuingCardholder(StripeModel):
    stripe_class = stripe.issuing.Cardholder

    class Meta:
        db_table = "djstripe_issuing_cardholder"


class IssuingDispute(StripeModel):
    stripe_class = stripe.issuing.Dispute

    class Meta:
        db_table = "djstripe_issuing_dispute"


class IssuingTransaction(StripeModel):
    stripe_class = stripe.issuing.Transaction

    class Meta:
        db_table = "djstripe_issuing_transaction"
