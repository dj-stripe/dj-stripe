import warnings

import stripe
from django.db import models

from .. import enums
from .. import settings as djstripe_settings
from ..fields import (
	JSONField, StripeCurrencyCodeField, StripeDecimalCurrencyAmountField,
	StripeEnumField, StripeIdField, StripeQuantumCurrencyAmountField
)
from ..managers import TransferManager
from .base import StripeModel


class Account(StripeModel):
	"""
	Stripe documentation: https://stripe.com/docs/api#account
	"""

	stripe_class = stripe.Account

	business_logo = models.ForeignKey("FileUpload", on_delete=models.SET_NULL, null=True)
	business_name = models.CharField(
		max_length=255,
		default="",
		blank=True,
		help_text="The publicly visible name of the business",
	)
	business_primary_color = models.CharField(
		max_length=7,
		default="",
		blank=True,
		help_text=(
			"A CSS hex color value representing the primary branding color for this account"
		),
	)
	business_url = models.CharField(
		max_length=200,
		default="",
		blank=True,
		help_text=("The publicly visible website of the business"),
	)
	charges_enabled = models.BooleanField(
		help_text="Whether the account can create live charges"
	)
	country = models.CharField(max_length=2, help_text="The country of the account")
	debit_negative_balances = models.NullBooleanField(
		null=True,
		blank=True,
		default=False,
		help_text=(
			"A Boolean indicating if Stripe should try to reclaim negative "
			"balances from an attached bank account."
		),
	)
	decline_charge_on = JSONField(
		null=True,
		blank=True,
		help_text=(
			"Account-level settings to automatically decline certain types "
			"of charges regardless of the decision of the card issuer"
		),
	)
	default_currency = StripeCurrencyCodeField(
		help_text="The currency this account has chosen to use as the default"
	)
	details_submitted = models.BooleanField(
		help_text=(
			"Whether account details have been submitted. "
			"Standard accounts cannot receive payouts before this is true."
		)
	)
	display_name = models.CharField(
		max_length=255,
		default="",
		blank=True,
		help_text=(
			"The display name for this account. "
			"This is used on the Stripe Dashboard to differentiate between accounts."
		),
	)
	email = models.CharField(max_length=255, help_text="The primary user’s email address.")
	# TODO external_accounts = ...
	legal_entity = JSONField(
		null=True,
		blank=True,
		help_text=(
			"Information about the legal entity itself, including about the associated account representative"
		),
	)
	payout_schedule = JSONField(
		null=True,
		blank=True,
		help_text=(
			"Details on when funds from charges are available, and when they are paid out to an external account."
		),
	)
	payout_statement_descriptor = models.CharField(
		max_length=255,
		default="",
		blank=True,
		help_text="The text that appears on the bank account statement for payouts.",
	)
	payouts_enabled = models.BooleanField(
		help_text="Whether Stripe can send payouts to this account"
	)
	product_description = models.CharField(
		max_length=255,
		default="",
		blank=True,
		help_text=(
			"Internal-only description of the product sold or service provided by the business. "
			"It’s used by Stripe for risk and underwriting purposes."
		),
	)
	statement_descriptor = models.CharField(
		max_length=255,
		default="",
		blank=True,
		help_text=(
			"The default text that appears on credit card statements when a charge is made directly on the account"
		),
	)
	support_email = models.CharField(
		max_length=255,
		default="",
		blank=True,
		help_text="A publicly shareable support email address for the business",
	)
	support_phone = models.CharField(
		max_length=255,
		default="",
		blank=True,
		help_text="A publicly shareable support phone number for the business",
	)
	support_url = models.CharField(
		max_length=200,
		default="",
		blank=True,
		help_text="A publicly shareable URL that provides support for this account",
	)
	timezone = models.CharField(
		max_length=50, help_text="The timezone used in the Stripe Dashboard for this account."
	)
	type = StripeEnumField(enum=enums.AccountType, help_text="The Stripe account type.")
	tos_acceptance = JSONField(
		null=True,
		blank=True,
		help_text="Details on the acceptance of the Stripe Services Agreement",
	)
	verification = JSONField(
		null=True,
		blank=True,
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
		account_data = cls.stripe_class.retrieve(api_key=djstripe_settings.STRIPE_SECRET_KEY)

		return cls._get_or_create_from_stripe_object(account_data)[0]

	def __str__(self):
		return self.display_name or self.business_name


class ApplicationFee(StripeModel):
	"""
	When you collect a transaction fee on top of a charge made for your
	user (using Connect), an ApplicationFee is created in your account.

	Stripe documentation: https://stripe.com/docs/api#application_fees
	"""

	stripe_class = stripe.ApplicationFee

	amount = StripeQuantumCurrencyAmountField(help_text="Amount earned.")
	amount_refunded = StripeQuantumCurrencyAmountField(
		help_text="Amount refunded (can be less than the amount attribute "
		"on the fee if a partial refund was issued)"
	)
	# TODO application = ...
	balance_transaction = models.ForeignKey(
		"BalanceTransaction",
		on_delete=models.CASCADE,
		help_text="Balance transaction that describes the impact on your account balance.",
	)
	charge = models.ForeignKey(
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

	amount = StripeQuantumCurrencyAmountField(help_text="Amount refunded.")
	balance_transaction = models.ForeignKey(
		"BalanceTransaction",
		on_delete=models.CASCADE,
		help_text="Balance transaction that describes the impact on your account balance.",
	)
	currency = StripeCurrencyCodeField()
	fee = models.ForeignKey(
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
		help_text="Currencies that can be accepted in the specific country (for transfers)."
	)
	supported_payment_currencies = JSONField(
		help_text="Currencies that can be accepted in the specified country (for payments)."
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
		help_text="The amount reversed (can be less than the amount attribute on the transfer if a partial "
		"reversal was issued).",
	)
	balance_transaction = models.ForeignKey(
		"BalanceTransaction",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		help_text="Balance transaction that describes the impact on your account balance.",
	)
	currency = StripeCurrencyCodeField()
	# TODO: Link destination to Card, Account, or Bank Account Models
	destination = StripeIdField(
		help_text="ID of the bank account, card, or Stripe account the transfer was sent to."
	)
	destination_payment = StripeIdField(
		null=True,
		blank=True,
		help_text="If the destination is a Stripe account, this will be the ID of the payment that the destination "
		"account received for the transfer.",
	)
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
	balance_transaction = models.ForeignKey(
		"BalanceTransaction",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="transfer_reversals",
		help_text="Balance transaction that describes the impact on your account balance.",
	)
	currency = StripeCurrencyCodeField()
	transfer = models.ForeignKey(
		"Transfer",
		on_delete=models.CASCADE,
		help_text="The transfer that was reversed.",
		related_name="reversals",
	)
