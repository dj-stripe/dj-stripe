import warnings

import stripe
from django.db import models

from .. import enums
from .. import settings as djstripe_settings
from ..fields import (
    StripeCharField, StripeDecimalCurrencyAmountField,
    StripeEnumField, StripeIdField, StripeJSONField
)
from ..managers import TransferManager
from .base import StripeObject


class Account(StripeObject):
    """
    Stripe documentation: https://stripe.com/docs/api#account
    """
    stripe_class = stripe.Account

    business_logo = models.ForeignKey(
        "FileUpload", on_delete=models.SET_NULL, null=True
    )
    business_name = StripeCharField(
        max_length=255,
        null=True, blank=True,
        help_text=("The publicly visible name of the business"),
    )
    business_primary_color = StripeCharField(
        max_length=7,
        null=True, blank=True,
        help_text=(
            "A CSS hex color value representing the primary branding color for this account"
        ),
    )
    business_url = StripeCharField(
        max_length=200,
        null=True,
        help_text=("The publicly visible website of the business"),
    )
    charges_enabled = models.BooleanField(
        help_text="Whether the account can create live charges"
    )
    country = StripeCharField(max_length=2, help_text="The country of the account")
    debit_negative_balances = models.NullBooleanField(
        null=True, blank=True,
        default=False,
        help_text=(
            "A Boolean indicating if Stripe should try to reclaim negative "
            "balances from an attached bank account."
        ),
    )
    decline_charge_on = StripeJSONField(
        null=True, blank=True,
        help_text=(
            "Account-level settings to automatically decline certain types "
            "of charges regardless of the decision of the card issuer"
        ),
    )
    default_currency = StripeCharField(
        max_length=3,
        help_text=("The currency this account has chosen to use as the default"),
    )
    details_submitted = models.BooleanField(
        help_text=(
            "Whether account details have been submitted. "
            "Standard accounts cannot receive payouts before this is true."
        )
    )
    display_name = StripeCharField(
        max_length=255,
        help_text=(
            "The display name for this account. "
            "This is used on the Stripe Dashboard to differentiate between accounts."
        ),
    )
    email = StripeCharField(
        max_length=255, help_text="The primary user’s email address."
    )
    # TODO external_accounts = ...
    legal_entity = StripeJSONField(
        null=True, blank=True,
        help_text=(
            "Information about the legal entity itself, including about the associated account representative"
        ),
    )
    payout_schedule = StripeJSONField(
        null=True, blank=True,
        help_text=(
            "Details on when funds from charges are available, and when they are paid out to an external account."
        ),
    )
    payout_statement_descriptor = StripeCharField(
        max_length=255,
        default="",
        null=True, blank=True,
        help_text="The text that appears on the bank account statement for payouts.",
    )
    payouts_enabled = models.BooleanField(
        help_text="Whether Stripe can send payouts to this account"
    )
    product_description = StripeCharField(
        max_length=255,
        null=True, blank=True,
        help_text=(
            "Internal-only description of the product sold or service provided by the business. "
            "It’s used by Stripe for risk and underwriting purposes."
        ),
    )
    statement_descriptor = StripeCharField(
        max_length=255,
        default="",
        help_text=(
            "The default text that appears on credit card statements when a charge is made directly on the account"
        ),
    )
    support_email = StripeCharField(
        max_length=255,
        help_text=("A publicly shareable support email address for the business"),
    )
    support_phone = StripeCharField(
        max_length=255,
        help_text=("A publicly shareable support phone number for the business"),
    )
    support_url = StripeCharField(
        max_length=200,
        null=True, blank=True,
        help_text=("A publicly shareable URL that provides support for this account"),
    )
    timezone = StripeCharField(
        max_length=50,
        help_text=("The timezone used in the Stripe Dashboard for this account."),
    )
    type = StripeEnumField(enum=enums.AccountType, help_text="The Stripe account type.")
    tos_acceptance = StripeJSONField(
        null=True, blank=True,
        help_text=("Details on the acceptance of the Stripe Services Agreement"),
    )
    verification = StripeJSONField(
        null=True, blank=True,
        help_text=(
            "Information on the verification state of the account, "
            "including what information is needed and by when"
        ),
    )

    @classmethod
    def get_connected_account_from_token(cls, access_token):
        account_data = cls.stripe_class.retrieve(api_key=access_token)

        return cls._get_or_create_from_stripe_object(account_data)[0]

    @classmethod
    def get_default_account(cls):
        account_data = cls.stripe_class.retrieve(
            api_key=djstripe_settings.STRIPE_SECRET_KEY
        )

        return cls._get_or_create_from_stripe_object(account_data)[0]

    def __str__(self):
        return self.display_name or self.business_name


class Transfer(StripeObject):
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
        null=True, blank=True,
        help_text="The amount reversed (can be less than the amount attribute on the transfer if a partial "
        "reversal was issued).",
    )
    currency = StripeCharField(
        max_length=3, help_text="Three-letter ISO currency code."
    )
    # TODO: Link destination to Card, Account, or Bank Account Models
    destination = StripeIdField(
        help_text="ID of the bank account, card, or Stripe account the transfer was sent to."
    )
    destination_payment = StripeIdField(
        null=True, blank=True,
        help_text="If the destination is a Stripe account, this will be the ID of the payment that the destination "
        "account received for the transfer.",
    )
    # reversals = ...
    reversed = models.BooleanField(
        default=False,
        help_text="Whether or not the transfer has been fully reversed. If the transfer is only partially "
        "reversed, this attribute will still be false.",
    )
    source_transaction = StripeIdField(
        null=True,
        help_text="ID of the charge (or other transaction) that was used to fund the transfer. "
        "If null, the transfer was funded from the available balance.",
    )
    source_type = StripeEnumField(
        enum=enums.LegacySourceType,
        help_text=("The source balance from which this transfer came."),
    )
    transfer_group = StripeCharField(
        max_length=255,
        null=True, blank=True,
        help_text="A string that identifies this transaction as part of a group.",
    )

    @property
    def fee(self):
        if self.balance_transaction:
            return self.balance_transaction.fee

    @property
    def fee_details(self):
        warnings.warn(
            "Transfer.fee_details is deprecated and will be dropped in 1.4.0. "
            "Use Transfer.balance_transaction.fee_details instead.",
            DeprecationWarning
        )
        if self.balance_transaction:
            return self.balance_transaction.fee_details

    def str_parts(self):
        return [
            "amount={amount}".format(amount=self.amount),
        ] + super().str_parts()
