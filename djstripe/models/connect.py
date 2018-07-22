import stripe
from django.db import models

from .. import enums
from .. import settings as djstripe_settings
from ..fields import (
    StripeBooleanField, StripeCharField, StripeCurrencyField,
    StripeDateTimeField, StripeEnumField, StripeIdField,
    StripeJSONField, StripeNullBooleanField, StripeTextField
)
from ..managers import TransferManager
from .base import StripeObject


class Account(StripeObject):
    stripe_class = stripe.Account

    business_logo = models.ForeignKey(
        "FileUpload", on_delete=models.SET_NULL, null=True
    )
    business_name = StripeCharField(
        max_length=255,
        stripe_required=False,
        help_text=("The publicly visible name of the business"),
    )
    business_primary_color = StripeCharField(
        max_length=7,
        stripe_required=False,
        help_text=(
            "A CSS hex color value representing the primary branding color for this account"
        ),
    )
    business_url = StripeCharField(
        max_length=200,
        null=True,
        help_text=("The publicly visible website of the business"),
    )
    charges_enabled = StripeBooleanField(
        help_text="Whether the account can create live charges"
    )
    country = StripeCharField(max_length=2, help_text="The country of the account")
    debit_negative_balances = StripeNullBooleanField(
        stripe_required=False,
        default=False,
        help_text=(
            "A Boolean indicating if Stripe should try to reclaim negative "
            "balances from an attached bank account."
        ),
    )
    decline_charge_on = StripeJSONField(
        stripe_required=False,
        help_text=(
            "Account-level settings to automatically decline certain types "
            "of charges regardless of the decision of the card issuer"
        ),
    )
    default_currency = StripeCharField(
        max_length=3,
        help_text=("The currency this account has chosen to use as the default"),
    )
    details_submitted = StripeBooleanField(
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
        stripe_required=False,
        help_text=(
            "Information about the legal entity itself, including about the associated account representative"
        ),
    )
    payout_schedule = StripeJSONField(
        stripe_required=False,
        help_text=(
            "Details on when funds from charges are available, and when they are paid out to an external account."
        ),
    )
    payout_statement_descriptor = StripeCharField(
        max_length=255,
        default="",
        stripe_required=False,
        help_text="The text that appears on the bank account statement for payouts.",
    )
    payouts_enabled = StripeBooleanField(
        help_text="Whether Stripe can send payouts to this account"
    )
    product_description = StripeCharField(
        max_length=255,
        stripe_required=False,
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
        stripe_required=False,
        help_text=("A publicly shareable URL that provides support for this account"),
    )
    timezone = StripeCharField(
        max_length=50,
        help_text=("The timezone used in the Stripe Dashboard for this account."),
    )
    type = StripeEnumField(enum=enums.AccountType, help_text="The Stripe account type.")
    tos_acceptance = StripeJSONField(
        stripe_required=False,
        help_text=("Details on the acceptance of the Stripe Services Agreement"),
    )
    verification = StripeJSONField(
        stripe_required=False,
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
    When Stripe sends you money or you initiate a transfer to a bank account, debit card, or
    connected Stripe account, a transfer object will be created.
    (Source: https://stripe.com/docs/api/python#transfers)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:

    * **object** - Unnecessary. Just check the model name.
    * **application_fee** - #
    * **balance_transaction** - #
    * **reversals** - #

    .. TODO: Link destination to Card, Account, or Bank Account Models

    .. attention:: Stripe API_VERSION: model fields and methods audited to 2016-03-07 - @kavdev
    """

    stripe_class = stripe.Transfer
    expand_fields = ["balance_transaction"]
    stripe_dashboard_item_name = "transfers"

    objects = TransferManager()

    amount = StripeCurrencyField(help_text="The amount transferred")
    amount_reversed = StripeCurrencyField(
        stripe_required=False,
        help_text="The amount reversed (can be less than the amount attribute on the transfer if a partial "
        "reversal was issued).",
    )
    currency = StripeCharField(
        max_length=3, help_text="Three-letter ISO currency code."
    )
    destination = StripeIdField(
        help_text="ID of the bank account, card, or Stripe account the transfer was sent to."
    )
    destination_payment = StripeIdField(
        stripe_required=False,
        help_text="If the destination is a Stripe account, this will be the ID of the payment that the destination "
        "account received for the transfer.",
    )
    # reversals = ...
    reversed = StripeBooleanField(
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
        stripe_required=False,
        help_text="A string that identifies this transaction as part of a group.",
    )

    # DEPRECATED Fields
    date = StripeDateTimeField(
        help_text="Date the transfer is scheduled to arrive in the bank. This doesn't factor in delays like "
        "weekends or bank holidays."
    )
    destination_type = StripeCharField(
        stripe_name="type",
        max_length=14,
        stripe_required=False,
        help_text="The type of the transfer destination.",
    )
    failure_code = StripeEnumField(
        enum=enums.PayoutFailureCode,
        stripe_required=False,
        help_text="Error code explaining reason for transfer failure if available. "
        "See https://stripe.com/docs/api/python#transfer_failures.",
    )
    failure_message = StripeTextField(
        stripe_required=False,
        help_text="Message to user further explaining reason for transfer failure if available.",
    )
    statement_descriptor = StripeCharField(
        max_length=22,
        null=True,
        help_text="An arbitrary string to be displayed on your customer's credit card statement. The statement "
        "description may not include <>\"' characters, and will appear on your customer's statement in capital "
        "letters. Non-ASCII characters are automatically stripped. While most banks display this information "
        "consistently, some may display it incorrectly or not at all.",
    )
    status = StripeEnumField(
        enum=enums.PayoutStatus,
        stripe_required=False,
        help_text="The current status of the transfer. A transfer will be pending until it is submitted to the bank, "
        "at which point it becomes in_transit. It will then change to paid if the transaction goes through. "
        "If it does not go through successfully, its status will change to failed or canceled.",
    )

    # Balance transaction can be null if the transfer failed
    fee = StripeCurrencyField(stripe_required=False, nested_name="balance_transaction")
    fee_details = StripeJSONField(
        stripe_required=False, nested_name="balance_transaction"
    )

    def str_parts(self):
        return [
            "amount={amount}".format(amount=self.amount),
            "status={status}".format(status=self.status),
        ] + super().str_parts()
