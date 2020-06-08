import stripe
from django.db import models

from .. import enums
from ..fields import (
    JSONField,
    StripeCurrencyCodeField,
    StripeDecimalCurrencyAmountField,
    StripeEnumField,
    StripeForeignKey,
    StripeIdField,
    StripeQuantumCurrencyAmountField,
)
from ..managers import TransferManager
from .base import StripeModel


class ApplicationFee(StripeModel):
    """
    When you collect a transaction fee on top of a charge made for your
    user (using Connect), an ApplicationFee is created in your account.

    Stripe documentation: https://stripe.com/docs/api#application_fees
    """

    stripe_class = stripe.ApplicationFee

    amount = StripeQuantumCurrencyAmountField(help_text="Amount earned, in cents.")
    amount_refunded = StripeQuantumCurrencyAmountField(
        help_text="Amount in cents refunded (can be less than the amount attribute "
        "on the fee if a partial refund was issued)"
    )
    # TODO application = ...
    balance_transaction = StripeForeignKey(
        "BalanceTransaction",
        on_delete=models.CASCADE,
        help_text="Balance transaction that describes the impact on your account"
        " balance.",
    )
    charge = StripeForeignKey(
        "Charge",
        on_delete=models.CASCADE,
        help_text="The charge that the application fee was taken from.",
    )
    currency = StripeCurrencyCodeField()
    # TODO originating_transaction = ... (refs. both Charge and Transfer)
    refunded = models.BooleanField(
        help_text=(
            "Whether the fee has been fully refunded. If the fee is only "
            "partially refunded, this attribute will still be false."
        )
    )


class ApplicationFeeRefund(StripeModel):
    """
    ApplicationFeeRefund objects allow you to refund an ApplicationFee that
    has previously been created but not yet refunded.
    Funds will be refunded to the Stripe account from which the fee was
    originally collected.

    Stripe documentation: https://stripe.com/docs/api#fee_refunds
    """

    description = None

    amount = StripeQuantumCurrencyAmountField(help_text="Amount refunded, in cents.")
    balance_transaction = StripeForeignKey(
        "BalanceTransaction",
        on_delete=models.CASCADE,
        help_text="Balance transaction that describes the impact on your account "
        "balance.",
    )
    currency = StripeCurrencyCodeField()
    fee = StripeForeignKey(
        "ApplicationFee",
        on_delete=models.CASCADE,
        related_name="refunds",
        help_text="The application fee that was refunded",
    )


class CountrySpec(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/api#country_specs
    """

    stripe_class = stripe.CountrySpec

    id = models.CharField(max_length=2, primary_key=True, serialize=True)

    default_currency = StripeCurrencyCodeField(
        help_text=(
            "The default currency for this country. "
            "This applies to both payment methods and bank accounts."
        )
    )
    supported_bank_account_currencies = JSONField(
        help_text="Currencies that can be accepted in the specific country"
        " (for transfers)."
    )
    supported_payment_currencies = JSONField(
        help_text="Currencies that can be accepted in the specified country"
        " (for payments)."
    )
    supported_payment_methods = JSONField(
        help_text="Payment methods available in the specified country."
    )
    supported_transfer_countries = JSONField(
        help_text="Countries that can accept transfers from the specified country."
    )
    verification_fields = JSONField(
        help_text="Lists the types of verification data needed to keep an account open."
    )

    # Get rid of core common fields
    djstripe_id = None
    created = None
    description = None
    livemode = True
    metadata = None

    class Meta:
        pass


class Transfer(StripeModel):
    """
    When Stripe sends you money or you initiate a transfer to a bank account,
    debit card, or connected Stripe account, a transfer object will be created.

    Stripe documentation: https://stripe.com/docs/api/python#transfers
    """

    stripe_class = stripe.Transfer
    expand_fields = ["balance_transaction"]
    stripe_dashboard_item_name = "transfers"

    objects = TransferManager()

    amount = StripeDecimalCurrencyAmountField(help_text="The amount transferred")
    amount_reversed = StripeDecimalCurrencyAmountField(
        null=True,
        blank=True,
        help_text="The amount (as decimal) reversed (can be less than the amount "
        "attribute on the transfer if a partial reversal was issued).",
    )
    balance_transaction = StripeForeignKey(
        "BalanceTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Balance transaction that describes the impact on your account"
        " balance.",
    )
    currency = StripeCurrencyCodeField()
    # TODO: Link destination to Card, Account, or Bank Account Models
    destination = StripeIdField(
        help_text="ID of the bank account, card, or Stripe account the transfer was "
        "sent to."
    )
    destination_payment = StripeIdField(
        null=True,
        blank=True,
        help_text="If the destination is a Stripe account, this will be the ID of the "
        "payment that the destination account received for the transfer.",
    )
    reversed = models.BooleanField(
        default=False,
        help_text="Whether or not the transfer has been fully reversed. "
        "If the transfer is only partially reversed, this attribute will still "
        "be false.",
    )
    source_transaction = StripeIdField(
        null=True,
        help_text="ID of the charge (or other transaction) that was used to fund "
        "the transfer. If null, the transfer was funded from the available balance.",
    )
    source_type = StripeEnumField(
        enum=enums.LegacySourceType,
        help_text="The source balance from which this transfer came.",
    )
    transfer_group = models.CharField(
        max_length=255,
        default="",
        blank=True,
        help_text="A string that identifies this transaction as part of a group.",
    )

    @property
    def fee(self):
        if self.balance_transaction:
            return self.balance_transaction.fee

    def str_parts(self):
        return ["amount={amount}".format(amount=self.amount)] + super().str_parts()


class TransferReversal(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/api#transfer_reversals
    """

    stripe_class = stripe.Transfer

    amount = StripeQuantumCurrencyAmountField(help_text="Amount, in cents.")
    balance_transaction = StripeForeignKey(
        "BalanceTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transfer_reversals",
        help_text="Balance transaction that describes the impact on your account "
        "balance.",
    )
    currency = StripeCurrencyCodeField()
    transfer = StripeForeignKey(
        "Transfer",
        on_delete=models.CASCADE,
        help_text="The transfer that was reversed.",
        related_name="reversals",
    )
