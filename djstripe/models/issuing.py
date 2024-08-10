import stripe

from .base import StripeModel


class Authorization(StripeModel):
    stripe_class = stripe.issuing.Authorization

    class Meta:
        db_table = "djstripe_issuing_authorization"


class Card(StripeModel):
    stripe_class = stripe.issuing.Card

    class Meta:
        db_table = "djstripe_issuing_card"


class Cardholder(StripeModel):
    stripe_class = stripe.issuing.Cardholder

    class Meta:
        db_table = "djstripe_issuing_cardholder"


class Dispute(StripeModel):
    stripe_class = stripe.issuing.Dispute

    class Meta:
        db_table = "djstripe_issuing_dispute"


class Transaction(StripeModel):
    stripe_class = stripe.issuing.Transaction

    class Meta:
        db_table = "djstripe_issuing_transaction"
