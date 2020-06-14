import stripe
from django.db import models, transaction

from .. import enums
from .. import settings as djstripe_settings
from ..fields import (
    JSONField,
    StripeCurrencyCodeField,
    StripeEnumField,
    StripeForeignKey,
)
from .api import APIKey
from .base import StripeModel


class Account(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/api#account
    """

    djstripe_owner_account = None

    stripe_class = stripe.Account
    # Special handling of the icon and logo fields, they moved to settings.branding
    # in Stripe 2019-02-19 but we want them as ForeignKeys
    branding_icon = StripeForeignKey(
        "FileUpload",
        on_delete=models.SET_NULL,
        null=True,
        related_name="icon_account",
        help_text="An icon for the account. Must be square and at least 128px x 128px.",
    )
    branding_logo = StripeForeignKey(
        "FileUpload",
        on_delete=models.SET_NULL,
        null=True,
        related_name="logo_account",
        help_text="A logo for the account that will be used in Checkout instead of "
        "the icon and without the account’s name next to it if provided. "
        "Must be at least 128px x 128px.",
    )
    business_profile = JSONField(
        null=True, blank=True, help_text="Optional information related to the business."
    )
    business_type = StripeEnumField(
        enum=enums.BusinessType, default="", blank=True, help_text="The business type."
    )
    charges_enabled = models.BooleanField(
        help_text="Whether the account can create live charges"
    )
    country = models.CharField(max_length=2, help_text="The country of the account")
    company = JSONField(
        null=True,
        blank=True,
        help_text=(
            "Information about the company or business. "
            "This field is null unless business_type is set to company."
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
    email = models.CharField(
        max_length=255, help_text="The primary user’s email address."
    )
    # TODO external_accounts = ...
    individual = JSONField(
        null=True,
        blank=True,
        help_text=(
            "Information about the person represented by the account. "
            "This field is null unless business_type is set to individual."
        ),
    )
    payouts_enabled = models.BooleanField(
        null=True, help_text="Whether Stripe can send payouts to this account"
    )
    product_description = models.CharField(
        max_length=255,
        default="",
        blank=True,
        help_text="Internal-only description of the product sold or service provided "
        "by the business. It’s used by Stripe for risk and underwriting purposes.",
    )
    requirements = JSONField(
        null=True,
        blank=True,
        help_text="Information about the requirements for the account, "
        "including what information needs to be collected, and by when.",
    )
    settings = JSONField(
        null=True,
        blank=True,
        help_text=(
            "Account options for customizing how the account functions within Stripe."
        ),
    )
    type = StripeEnumField(enum=enums.AccountType, help_text="The Stripe account type.")
    tos_acceptance = JSONField(
        null=True,
        blank=True,
        help_text="Details on the acceptance of the Stripe Services Agreement",
    )

    @property
    def business_url(self):
        """
        The business’s publicly available website.
        :rtype: Optional[str]
        """
        return (self.business_profile or {}).get("url")

    @classmethod
    def get_connected_account_from_token(cls, access_token):
        account_data = cls.stripe_class.retrieve(api_key=access_token)

        return cls._get_or_create_from_stripe_object(account_data)[0]

    @classmethod
    def get_default_account(cls):
        # As of API version 2020-03-02, there is no permission that can allow
        # restricted keys to call GET /v1/account
        if djstripe_settings.STRIPE_SECRET_KEY.startswith("rk_"):
            return None

        account_data = cls.stripe_class.retrieve(
            api_key=djstripe_settings.STRIPE_SECRET_KEY
        )

        return cls._get_or_create_from_stripe_object(account_data)[0]

    @classmethod
    def get_or_retrieve_for_api_key(cls, api_key: str):
        with transaction.atomic():
            apikey_instance, _ = APIKey.objects.get_or_create_by_api_key(api_key)
            if not apikey_instance.djstripe_owner_account:
                apikey_instance.refresh_account()

            return apikey_instance.djstripe_owner_account

    def __str__(self):
        settings = self.settings or {}
        business_profile = self.business_profile or {}
        return (
            settings.get("dashboard", {}).get("display_name")
            or business_profile.get("name")
            or super().__str__()
        )

    @classmethod  # noqa: C901
    def _manipulate_stripe_object_hook(cls, data):
        data = super()._manipulate_stripe_object_hook(data)

        # icon (formerly called business_logo)
        # logo (formerly called business_logo_large)
        # moved to settings.branding in Stripe 2019-02-19
        # but we'll keep them to provide the ForeignKey
        for old, new in [("branding_icon", "icon"), ("branding_logo", "logo")]:
            try:
                data[old] = data["settings"]["branding"][new]
            except KeyError:
                pass

        return data

    @classmethod
    def _create_from_stripe_object(
        cls,
        data,
        current_ids=None,
        pending_relations=None,
        save=True,
        stripe_account=None,
    ):
        """
        Set the stripe_account to the id of the Account instance being created.

        This ensures that the foreign-key relations that may exist in stripe are
        fetched using the appropriate connected account ID.
        """
        return super()._create_from_stripe_object(
            data=data,
            current_ids=current_ids,
            pending_relations=pending_relations,
            save=save,
            stripe_account=data["id"] if not stripe_account else stripe_account,
        )

    @classmethod
    def _find_owner_account(cls, data):
        # Account model never has an owner account (it's always itself)
        return None
