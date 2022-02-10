import re
from base64 import b64encode
from uuid import uuid4

from django.core.validators import RegexValidator
from django.db import IntegrityError, models, transaction
from django.forms import ValidationError

from ..enums import APIKeyType
from ..exceptions import InvalidStripeAPIKey
from ..fields import StripeEnumField
from .base import StripeModel

# A regex to validate API key format
API_KEY_REGEX = r"^(pk|sk|rk)_(test|live)_([a-zA-Z0-9]{24,99})"


def generate_api_key_id() -> str:
    b64_id = b64encode(uuid4().bytes).decode()
    generated_id = b64_id.rstrip("=").replace("+", "").replace("/", "")
    return f"djstripe_mk_{generated_id}"


def get_api_key_details_by_prefix(api_key: str):
    sre = re.match(API_KEY_REGEX, api_key)
    if not sre:
        raise InvalidStripeAPIKey(f"Invalid API key: {api_key!r}")

    key_type = {
        "pk": APIKeyType.publishable,
        "sk": APIKeyType.secret,
        "rk": APIKeyType.restricted,
    }.get(sre.group(1), "")
    livemode = {"test": False, "live": True}.get(sre.group(2))

    return key_type, livemode


class APIKeyManager(models.Manager):
    def get_or_create_by_api_key(self, secret: str):
        key_type, livemode = get_api_key_details_by_prefix(secret)
        return super().get_or_create(
            secret=secret, defaults={"type": key_type, "livemode": livemode}
        )


class APIKey(StripeModel):
    object = "api_key"

    id = models.CharField(max_length=255, default=generate_api_key_id, editable=False)
    type = StripeEnumField(enum=APIKeyType)
    name = models.CharField(
        "Key name",
        max_length=100,
        blank=True,
        help_text="An optional name to identify the key.",
    )
    secret = models.CharField(
        max_length=128,
        validators=[RegexValidator(regex=API_KEY_REGEX)],
        unique=True,
        help_text="The value of the key.",
    )

    livemode = models.BooleanField(
        help_text="Whether the key is valid for live or test mode."
    )
    description = None
    metadata = None
    objects = APIKeyManager()

    def get_stripe_dashboard_url(self):
        return self._get_base_stripe_dashboard_url() + "apikeys"

    def __str__(self):
        return self.name or self.secret_redacted

    def clean(self):
        if self.livemode is None or self.type is None:
            try:
                self.type, self.livemode = get_api_key_details_by_prefix(self.secret)
            except InvalidStripeAPIKey as e:
                raise ValidationError(str(e))

    def refresh_account(self, commit=True):
        from .account import Account

        if self.type != APIKeyType.secret:
            return

        account_data = Account.stripe_class.retrieve(api_key=self.secret)
        # NOTE: Do not immediately use _get_or_create_from_stripe_object() here.
        # Account needs to exist for things to work. Make a stub if necessary.
        account, created = Account.objects.get_or_create(
            id=account_data["id"],
            defaults={"charges_enabled": False, "details_submitted": False},
        )
        if created:
            # If it's just been created, now we can sync the account.
            Account.sync_from_stripe_data(account_data, api_key=self.secret)
        self.djstripe_owner_account = account
        if commit:
            try:
                # for non-existent accounts, due to djstripe_owner_account search for the
                # accounts themselves, trigerred by this method, the APIKey gets created before this method
                # can "commit". This results in an Integrity Error
                with transaction.atomic():
                    self.save()
            except IntegrityError:
                pass

    @property
    def secret_redacted(self) -> str:
        """
        Returns a redacted version of the secret, suitable for display purposes.

        Same algorithm used on the Stripe dashboard.
        """
        secret_prefix, _, secret_part = self.secret.rpartition("_")
        secret_part = secret_part[-4:]
        return f"{secret_prefix}_...{secret_part}"
