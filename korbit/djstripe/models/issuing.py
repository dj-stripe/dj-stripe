import stripe

from .base import StripeModel


class IssuingAuthorization(StripeModel):
    """
    When an issued card is used to make a purchase, an Issuing Authorization object is created.
    Authorizations must be approved for the purchase to be completed successfully.

    Stripe documentation: https://docs.stripe.com/api/issuing/authorizations?lang=python
    """

    stripe_class = stripe.issuing.Authorization

    class Meta:
        db_table = "djstripe_issuing_authorization"

    # https://docs.stripe.com/api/issuing/authorizations/object#issuing_authorization_object-amount
    @property
    def amount(self) -> int:
        return self.stripe_data["amount"]

    # https://docs.stripe.com/api/issuing/authorizations/object#issuing_authorization_object-approved
    @property
    def approved(self) -> bool:
        return self.stripe_data["approved"]

    # https://docs.stripe.com/api/issuing/authorizations/object#issuing_authorization_object-currency
    # TODO: Add currency enum

    # https://docs.stripe.com/api/issuing/authorizations/object#issuing_authorization_object-status
    # TODO: Add status enum


class IssuingCard(StripeModel):
    """
    You can create physical or virtual cards that are issued to cardholders.

    Stripe documentation: https://stripe.com/docs/api/issuing/cards?lang=python
    """

    stripe_class = stripe.issuing.Card

    class Meta:
        db_table = "djstripe_issuing_card"

    # https://docs.stripe.com/api/issuing/cards/object#issuing_card_object-cancellation_reason
    # TODO: Add cancellation enum

    # https://docs.stripe.com/api/issuing/cards/object#issuing_card_object-currency
    # TODO: Add currency enum

    # https://docs.stripe.com/api/issuing/cards/object#issuing_card_object-exp_month
    @property
    def exp_month(self) -> int:
        return self.stripe_data["exp_month"]

    # https://docs.stripe.com/api/issuing/cards/object#issuing_card_object-exp_year
    @property
    def exp_year(self) -> int:
        return self.stripe_data["exp_year"]

    # https://docs.stripe.com/api/issuing/cards/object#issuing_card_object-last4
    @property
    def last4(self) -> str:
        return self.stripe_data["last4"]

    # https://docs.stripe.com/api/issuing/cards/object#issuing_card_object-status
    # TODO: Add status

    # https://docs.stripe.com/api/issuing/cards/object#issuing_card_object-type
    # TODO: Add type


class IssuingCardholder(StripeModel):
    """
    An Issuing Cardholder object represents an individual or business entity who is issued cards.

    Stripe documentation: https://stripe.com/docs/api/issuing/cardholders?lang=python
    """

    stripe_class = stripe.issuing.Cardholder

    class Meta:
        db_table = "djstripe_issuing_cardholder"

    # https://docs.stripe.com/api/issuing/cardholders/object#issuing_cardholder_object-billing
    @property
    def billing(self) -> dict:
        return self.stripe_data["billing"]

    # https://docs.stripe.com/api/issuing/cardholders/object#issuing_cardholder_object-email
    @property
    def email(self) -> str | None:
        return self.stripe_data["email"]

    # https://docs.stripe.com/api/issuing/cardholders/object#issuing_cardholder_object-name
    @property
    def name(self) -> str:
        return self.stripe_data["name"]

    # https://docs.stripe.com/api/issuing/cardholders/object#issuing_cardholder_object-phone_number
    @property
    def phone_number(self) -> str | None:
        return self.stripe_data["phone_number"]


class IssuingDispute(StripeModel):
    """
    As a card issuer, you can dispute transactions that the cardholder does not recognize, suspects to be fraudulent, or has other issues with.

    Stripe documentation: https://stripe.com/docs/api/issuing/disputes?lang=python
    """

    stripe_class = stripe.issuing.Dispute

    class Meta:
        db_table = "djstripe_issuing_dispute"

    # https://docs.stripe.com/api/issuing/disputes/object#issuing_dispute_object-amount
    @property
    def amount(self) -> int:
        return self.stripe_data["amount"]

    # https://docs.stripe.com/api/issuing/disputes/object#issuing_dispute_object-balance_transactions
    @property
    def balance_transactions(self) -> list[dict | None]:
        return self.stripe_data["balance_transactions"]

    # https://docs.stripe.com/api/issuing/disputes/object#issuing_dispute_object-currency
    # TODO: Add currency enum

    # https://docs.stripe.com/api/issuing/disputes/object#issuing_dispute_object-status
    # TODO: Add status


class IssuingTransaction(StripeModel):
    """
    Any use of an issued card that results in funds entering or leaving your Stripe account, such as a completed purchase or refund, is represented by an Issuing Transaction object.

    Stripe documentation: https://stripe.com/docs/api/issuing/transactions?lang=python
    """

    stripe_class = stripe.issuing.Transaction

    class Meta:
        db_table = "djstripe_issuing_transaction"

    # https://docs.stripe.com/api/issuing/transactions/object#issuing_transaction_object-amount
    @property
    def amount(self) -> int:
        return self.stripe_data["amount"]

    # https://docs.stripe.com/api/issuing/transactions/object#issuing_transaction_object-currency
    # TODO: Add currency enum

    # https://docs.stripe.com/api/issuing/transactions/object#issuing_transaction_object-type
    # TODO: Add type enum
