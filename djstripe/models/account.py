import stripe
from django.db import models, transaction

from .. import enums
from ..enums import APIKeyType
from ..fields import JSONField, StripeCurrencyCodeField, StripeEnumField
from ..settings import djstripe_settings
from .api import APIKey, get_api_key_details_by_prefix
from .base import StripeModel, logger


class Account(StripeModel):
    """
    This is an object representing a Stripe account.

    You can retrieve it to see properties on the account like its
    current e-mail address or if the account is enabled yet to make live charges.

    Stripe documentation: https://stripe.com/docs/api/accounts?lang=python
    """

    stripe_class = stripe.Account
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
        max_length=255, help_text="The primary user's email address."
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
        "by the business. It's used by Stripe for risk and underwriting purposes.",
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

    def get_stripe_dashboard_url(self) -> str:
        """Get the stripe dashboard url for this object."""
        return (
            f"https://dashboard.stripe.com/{self.id}/"
            f"{'test/' if not self.livemode else ''}dashboard"
        )

    @property
    def default_api_key(self) -> str:
        return self.get_default_api_key()

    def get_default_api_key(self, livemode: bool = None) -> str:
        if livemode is None:
            livemode = self.livemode
            api_key = APIKey.objects.filter(
                djstripe_owner_account=self, type=APIKeyType.secret
            ).first()
        else:
            api_key = APIKey.objects.filter(
                djstripe_owner_account=self, type=APIKeyType.secret, livemode=livemode
            ).first()

        if api_key:
            return api_key.secret
        return djstripe_settings.get_default_api_key(livemode)

    @property
    def business_url(self) -> str:
        """
        The business's publicly available website.
        """
        if self.business_profile:
            return self.business_profile.get("url", "")
        return ""

    @classmethod
    def get_default_account(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY):
        # As of API version 2020-03-02, there is no permission that can allow
        # restricted keys to call GET /v1/account
        if djstripe_settings.STRIPE_SECRET_KEY.startswith("rk_"):
            return None

        account_data = cls.stripe_class.retrieve(api_key=api_key)

        return cls._get_or_create_from_stripe_object(account_data, api_key=api_key)[0]

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

    def api_reject(self, api_key=None, stripe_account=None, **kwargs):
        """
        Call the stripe API's reject operation for Account model

        :param api_key: The api key to use for this request.
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        """
        api_key = api_key or self.default_api_key
        # Prefer passed in stripe_account if set.
        if not stripe_account:
            stripe_account = self._get_stripe_account_id(api_key)

        return self.stripe_class.reject(
            self.id, api_key=api_key, stripe_account=stripe_account, **kwargs
        )

    @classmethod
    def _create_from_stripe_object(
        cls,
        data,
        current_ids=None,
        pending_relations=None,
        save=True,
        stripe_account=None,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
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
            api_key=api_key,
        )

    # "Special" handling of the icon and logo fields
    # Previously available as properties, they moved to
    # settings.branding in Stripe 2019-02-19.
    # Currently, they return a File ID
    @property
    def branding_icon(self):
        from ..models.core import File

        id = self.settings.get("branding", {}).get("icon")
        return File.objects.filter(id=id).first() if id else None

    @property
    def branding_logo(self):
        from ..models.core import File

        id = self.settings.get("branding", {}).get("logo")
        return File.objects.filter(id=id).first() if id else None

    def _attach_objects_post_save_hook(
        self,
        cls,
        data,
        pending_relations=None,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
    ):
        from ..models.core import File

        super()._attach_objects_post_save_hook(
            cls, data, pending_relations=pending_relations, api_key=api_key
        )

        # set the livemode if not returned by data
        if "livemode" not in data.keys() and self.djstripe_owner_account is not None:

            # Platform Account
            if self == self.djstripe_owner_account:
                self.livemode = None
            else:
                # Connected Account
                _, self.livemode = get_api_key_details_by_prefix(api_key)

        # save the updates
        self.save()

        # Retrieve and save the Files in the settings.branding object.
        for field in "icon", "logo":
            file_upload_id = self.settings and self.settings.get("branding", {}).get(
                field
            )
            if file_upload_id:
                try:
                    File.sync_from_stripe_data(
                        File(id=file_upload_id).api_retrieve(
                            stripe_account=self.id, api_key=api_key
                        ),
                        api_key=api_key,
                    )
                except stripe.error.PermissionError:
                    # No permission to retrieve the data with the key
                    logger.warning(
                        f"Cannot retrieve business branding {field} for acct {self.id} with the key."
                    )
                except stripe.error.InvalidRequestError as e:
                    if "a similar object exists in" in str(e):
                        # HACK around a Stripe bug.
                        # See #830 and commit c09d25f52bfdcf883e9eec0bf6c25af1771a644a
                        pass
                    else:
                        raise
                except stripe.error.AuthenticationError:
                    # This may happen if saving an account that has a logo, using
                    # a different API key to the default.
                    # OK, concretely, there is a chicken-and-egg problem here.
                    # But, the logo file object is not a particularly important thing.
                    # Until we have a better solution, just ignore this error.
                    pass
