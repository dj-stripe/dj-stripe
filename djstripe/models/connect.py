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
from ..settings import djstripe_settings
from .base import StripeBaseModel, StripeModel


# TODO Implement Full Webhook event support for ApplicationFee and ApplicationFee Refund Objects
class ApplicationFee(StripeModel):
    """
    When you collect a transaction fee on top of a charge made for your
    user (using Connect), an ApplicationFee is created in your account.

    Please note the model field charge exists on the Stripe Connected Account
    while the application_fee modelfield on Charge model exists on the Platform Account!

    Stripe documentation: https://stripe.com/docs/api#application_fees
    """

    stripe_class = stripe.ApplicationFee
    account = StripeForeignKey(
        "Account",
        on_delete=models.PROTECT,
        related_name="application_fees",
        help_text="ID of the Stripe account this fee was taken from.",
    )
    amount = StripeQuantumCurrencyAmountField(help_text="Amount earned, in cents.")
    amount_refunded = StripeQuantumCurrencyAmountField(
        help_text="Amount in cents refunded (can be less than the amount attribute "
        "on the fee if a partial refund was issued)"
    )
    # TODO application = ...
    # balance_transaction exists on the platform account
    balance_transaction = StripeForeignKey(
        "BalanceTransaction",
        on_delete=models.CASCADE,
        help_text="Balance transaction that describes the impact on your account"
        " balance.",
    )
    # charge exists on the Stripe Connected Account and not the Platform Account
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


# TODO Add Tests
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


class CountrySpec(StripeBaseModel):
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

    @classmethod
    def sync_from_stripe_data(cls, data) -> "CountrySpec":
        """
        Syncs this object from the stripe data provided.

        Foreign keys will also be retrieved and synced recursively.

        :param data: stripe object
        :type data: dict
        :rtype: cls
        """
        data_id = data["id"]

        supported_fields = (
            "default_currency",
            "supported_bank_account_currencies",
            "supported_payment_currencies",
            "supported_payment_methods",
            "supported_transfer_countries",
            "verification_fields",
        )

        instance, created = cls.objects.get_or_create(
            id=data_id,
            defaults={k: data[k] for k in supported_fields},
        )

        return instance

    def api_retrieve(self, api_key: str = None, stripe_account=None):
        if api_key is None:
            api_key = djstripe_settings.get_default_api_key(livemode=None)

        return self.stripe_class.retrieve(
            id=self.id,
            api_key=api_key,
            stripe_account=stripe_account,
        )


class Transfer(StripeModel):
    """
    When Stripe sends you money or you initiate a transfer to a bank account,
    debit card, or connected Stripe account, a transfer object will be created.

    Stripe documentation: https://stripe.com/docs/api?lang=python#transfers
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

    destination = StripeIdField(
        max_length=255,
        null=True,
        help_text="ID of the bank account, card, or Stripe account the transfer was sent to.",
    )

    # todo implement payment model (for some reason py ids are showing up in the charge model)
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

    def __str__(self):
        if self.reversed:
            # Complete Reversal
            return f"{self.human_readable_amount} Reversed"
        elif self.amount_reversed:
            # Partial Reversal
            return f"{self.human_readable_amount} Partially Reversed"
        # No Reversal
        return f"{self.human_readable_amount}"

    def _attach_objects_post_save_hook(self, cls, data, pending_relations=None):
        """
        Iterate over reversals on the Transfer object to create and/or sync
        TransferReversal objects
        """

        super()._attach_objects_post_save_hook(
            cls, data, pending_relations=pending_relations
        )

        # Transfer Reversals exist as a list on the Transfer Object
        for reversals_data in data.get("reversals").auto_paging_iter():
            TransferReversal.sync_from_stripe_data(reversals_data)


# TODO Add Tests
class TransferReversal(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/api#transfer_reversals
    """

    expand_fields = ["balance_transaction", "transfer"]

    # TransferReversal classmethods are derived from
    # and attached to the stripe.Transfer class
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

    def __str__(self):
        return str(self.transfer)

    @classmethod
    def _api_create(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        """
        Call the stripe API's create operation for this model.
        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """

        if not kwargs.get("id"):
            raise KeyError("Transfer Object ID is missing")

        try:
            Transfer.objects.get(id=kwargs["id"])
        except Transfer.DoesNotExist:
            raise

        return stripe.Transfer.create_reversal(api_key=api_key, **kwargs)

    def api_retrieve(self, api_key=None, stripe_account=None):
        """
        Call the stripe API's retrieve operation for this model.
        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        """
        nested_id = self.id
        id = self.transfer.id

        # Prefer passed in stripe_account if set.
        if not stripe_account:
            stripe_account = self._get_stripe_account_id(api_key)

        return stripe.Transfer.retrieve_reversal(
            id=id,
            nested_id=nested_id,
            api_key=api_key or self.default_api_key,
            expand=self.expand_fields,
            stripe_account=stripe_account,
        )

    @classmethod
    def api_list(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        """
        Call the stripe API's list operation for this model.
        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        See Stripe documentation for accepted kwargs for each object.
        :returns: an iterator over all items in the query
        """
        return stripe.Transfer.list_reversals(
            api_key=api_key, **kwargs
        ).auto_paging_iter()

    @classmethod
    def is_valid_object(cls, data):
        """
        Returns whether the data is a valid object for the class
        """
        return "object" in data and data["object"] == "transfer_reversal"
