"""
dj-stripe System Checks
"""
import re

from django.core import checks
from django.db.utils import DatabaseError

STRIPE_API_VERSION_PATTERN = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})(; [\w=]*)?$"
)


# 4 possibilities:
# Keys in admin and in settings
# Keys in admin and not in settings
# Keys not in admin but in settings
# Keys not in admin and not in settings
@checks.register("djstripe")
def check_stripe_api_key(app_configs=None, **kwargs):
    """Check the user has configured API live/test keys correctly."""

    def _check_stripe_api_in_settings(messages):
        if djstripe_settings.STRIPE_LIVE_MODE:
            if not djstripe_settings.LIVE_API_KEY.startswith(("sk_live_", "rk_live_")):
                msg = "Bad Stripe live API key."
                hint = 'STRIPE_LIVE_SECRET_KEY should start with "sk_live_"'
                messages.append(checks.Info(msg, hint=hint, id="djstripe.I003"))
        elif not djstripe_settings.TEST_API_KEY.startswith(("sk_test_", "rk_test_")):
            msg = "Bad Stripe test API key."
            hint = 'STRIPE_TEST_SECRET_KEY should start with "sk_test_"'
            messages.append(checks.Info(msg, hint=hint, id="djstripe.I004"))

    from djstripe.models import APIKey

    from .settings import djstripe_settings

    messages = []

    try:
        # get all APIKey objects in the db
        api_qs = APIKey.objects.all()

        if not api_qs.exists():
            msg = (
                "You don't have any API Keys in the database. Did you forget to add"
                " them?"
            )
            hint = (
                "Add STRIPE_TEST_SECRET_KEY and STRIPE_LIVE_SECRET_KEY directly from"
                " the Django Admin."
            )
            messages.append(checks.Info(msg, hint=hint, id="djstripe.I001"))

            # Keys not in admin but in settings
            if djstripe_settings.STRIPE_SECRET_KEY:
                msg = (
                    "Your keys are defined in the settings files. You can now add and"
                    " manage them directly from the django admin."
                )
                hint = (
                    "Add STRIPE_TEST_SECRET_KEY and STRIPE_LIVE_SECRET_KEY directly"
                    " from the Django Admin."
                )
                messages.append(checks.Info(msg, hint=hint, id="djstripe.I002"))

                # Ensure keys defined in settings files are valid
                _check_stripe_api_in_settings(messages)

        # Keys in admin and in settings
        elif djstripe_settings.STRIPE_SECRET_KEY:
            msg = (
                "Your keys are defined in the settings files and are also in the admin."
                " You can now add and manage them directly from the django admin."
            )
            hint = (
                "We suggest adding STRIPE_TEST_SECRET_KEY and STRIPE_LIVE_SECRET_KEY"
                " directly from the Django Admin. And removing them from the settings"
                " files."
            )
            messages.append(checks.Info(msg, hint=hint, id="djstripe.I002"))

            # Ensure keys defined in settings files are valid
            _check_stripe_api_in_settings(messages)

    except DatabaseError:
        # Skip the check - Database most likely not migrated yet
        return []

    return messages


def validate_stripe_api_version(version):
    """
    Check the API version is formatted correctly for Stripe.

    The expected format is `YYYY-MM-DD` (an iso8601 date) or
    for access to alpha or beta releases the expected format is: `YYYY-MM-DD; modelname_version=version_number`.
    Ex "2020-08-27; orders_beta=v3"

    :param version: The version to set for the Stripe API.
    :type version: ``str``
    :returns bool: Whether the version is formatted correctly.
    """
    return re.match(STRIPE_API_VERSION_PATTERN, version)


@checks.register("djstripe")
def check_stripe_api_version(app_configs=None, **kwargs):
    """Check the user has configured API version correctly."""
    from .settings import djstripe_settings

    messages = []
    default_version = djstripe_settings.DEFAULT_STRIPE_API_VERSION
    version = djstripe_settings.STRIPE_API_VERSION

    if not validate_stripe_api_version(version):
        msg = f"Invalid Stripe API version: {version!r}"
        hint = "STRIPE_API_VERSION should be formatted as: YYYY-MM-DD"
        messages.append(checks.Critical(msg, hint=hint, id="djstripe.C004"))

    if version != default_version:
        msg = (
            f"The Stripe API version has a non-default value of '{version!r}'. "
            "Non-default versions are not explicitly supported, and may "
            "cause compatibility issues."
        )
        hint = f"Use the dj-stripe default for Stripe API version: {default_version}"
        messages.append(checks.Warning(msg, hint=hint, id="djstripe.W001"))

    return messages


@checks.register("djstripe")
def check_stripe_api_host(app_configs=None, **kwargs):
    """
    Check that STRIPE_API_HOST is not being used in production.
    """
    from django.conf import settings

    messages = []

    if not settings.DEBUG and hasattr(settings, "STRIPE_API_HOST"):
        messages.append(
            checks.Warning(
                (
                    "STRIPE_API_HOST should not be set in production! "
                    "This is most likely unintended."
                ),
                hint="Remove STRIPE_API_HOST from your Django settings.",
                id="djstripe.W002",
            )
        )

    return messages


@checks.register("djstripe")
def check_webhook_secret(app_configs=None, **kwargs):
    """
    Check that DJSTRIPE_WEBHOOK_SECRET looks correct
    """

    def check_webhook_endpoint_secret(secret, messages, endpoint=None):
        if secret and not secret.startswith("whsec_"):
            if endpoint:
                extra_msg = (
                    f"The secret for Webhook Endpoint: {endpoint} does not look valid"
                )
            else:
                extra_msg = "DJSTRIPE_WEBHOOK_SECRET does not look valid"

            messages.append(
                checks.Warning(
                    extra_msg,
                    hint="It should start with whsec_...",
                    id="djstripe.W003",
                )
            )
        return messages

    from .models import WebhookEndpoint
    from .settings import djstripe_settings

    messages = []
    try:
        webhooks = list(WebhookEndpoint.objects.all())
    except DatabaseError:
        # skip the db-based check (db most likely not migrated yet)
        webhooks = []

    if webhooks:
        for endpoint in webhooks:
            secret = endpoint.secret
            # check secret
            check_webhook_endpoint_secret(secret, messages, endpoint=endpoint)
    else:
        secret = djstripe_settings.WEBHOOK_SECRET
        # check secret
        check_webhook_endpoint_secret(secret, messages)

    return messages


def _check_webhook_endpoint_validation(secret, messages, endpoint=None):
    if not secret:
        if endpoint:
            extra_msg = f"but Webhook Endpoint: {endpoint} has no secret set"
            secret_attr = "secret"
        else:
            extra_msg = "but DJSTRIPE_WEBHOOK_SECRET is not set"
            secret_attr = "DJSTRIPE_WEBHOOK_SECRET"

        messages.append(
            checks.Info(
                f"DJSTRIPE_WEBHOOK_VALIDATION is set to 'verify_signature' {extra_msg}",
                hint=(
                    f"Set {secret_attr} from Django shell or set"
                    " DJSTRIPE_WEBHOOK_VALIDATION='retrieve_event'"
                ),
                id="djstripe.I006",
            )
        )
    return messages


@checks.register("djstripe")
def check_webhook_validation(app_configs=None, **kwargs):
    """
    Check that DJSTRIPE_WEBHOOK_VALIDATION is valid
    """
    from .models import WebhookEndpoint
    from .settings import djstripe_settings

    setting_name = "DJSTRIPE_WEBHOOK_VALIDATION"

    messages = []

    validation_options = ("verify_signature", "retrieve_event")

    if djstripe_settings.WEBHOOK_VALIDATION is None:
        messages.append(
            checks.Warning(
                (
                    "Webhook validation is disabled, this is a security risk if the "
                    "webhook view is enabled"
                ),
                hint=f"Set {setting_name} to one of: {validation_options}",
                id="djstripe.W004",
            )
        )
    elif djstripe_settings.WEBHOOK_VALIDATION == "verify_signature":
        try:
            webhooks = list(WebhookEndpoint.objects.all())
        except DatabaseError:
            # Skip the db-based check (database most likely not migrated yet)
            webhooks = []

        if webhooks:
            for endpoint in webhooks:
                secret = endpoint.secret
                # check secret
                _check_webhook_endpoint_validation(secret, messages, endpoint=endpoint)
        else:
            secret = djstripe_settings.WEBHOOK_SECRET
            # check secret
            _check_webhook_endpoint_validation(secret, messages)

    elif djstripe_settings.WEBHOOK_VALIDATION not in validation_options:
        messages.append(
            checks.Critical(
                f"{setting_name} is invalid",
                hint=f"Set {setting_name} to one of: {validation_options} or None",
                id="djstripe.C007",
            )
        )

    return messages


@checks.register("djstripe")
def check_webhook_endpoint_has_secret(app_configs=None, **kwargs):
    """Checks if all Webhook Endpoints have not empty secrets."""
    from djstripe.models import WebhookEndpoint

    messages = []

    try:
        qs = list(WebhookEndpoint.objects.filter(secret="").all())
    except DatabaseError:
        # Skip the check - Database most likely not migrated yet
        return []

    for webhook in qs:
        webhook_url = webhook.get_stripe_dashboard_url()
        messages.append(
            checks.Warning(
                (
                    f"The secret of Webhook Endpoint: {webhook} is not populated "
                    "in the db. Events sent to it will not work properly."
                ),
                hint=(
                    "This can happen if it was deleted and resynced as Stripe "
                    "sends the webhook secret ONLY on the creation call. "
                    "Please use the django shell and update the secret with "
                    f"the value from {webhook_url}"
                ),
                id="djstripe.W005",
            )
        )

    return messages


@checks.register("djstripe")
def check_subscriber_key_length(app_configs=None, **kwargs):
    """
    Check that DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY fits in metadata.

    Docs: https://stripe.com/docs/api#metadata
    """
    from .settings import djstripe_settings

    messages = []

    key = djstripe_settings.SUBSCRIBER_CUSTOMER_KEY
    key_max_length = 40
    if key and len(key) > key_max_length:
        messages.append(
            checks.Error(
                (
                    "DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY must be no more than "
                    f"{key_max_length} characters long"
                ),
                hint=f"Current value: {key!r}",
                id="djstripe.E001",
            )
        )

    return messages


@checks.register("djstripe")
def check_djstripe_settings_foreign_key_to_field(app_configs=None, **kwargs):
    """
    Check that DJSTRIPE_FOREIGN_KEY_TO_FIELD is set to a valid value.
    """
    from django.conf import settings

    setting_name = "DJSTRIPE_FOREIGN_KEY_TO_FIELD"
    hint = (
        f'Set {setting_name} to "id" if this is a new installation, '
        'otherwise set it to "djstripe_id".'
    )
    messages = []

    if not hasattr(settings, setting_name):
        messages.append(
            checks.Error(
                f"{setting_name} is not set.",
                hint=hint,
                id="djstripe.E002",
            )
        )
    elif getattr(settings, setting_name) not in ("id", "djstripe_id"):
        setting_value = getattr(settings, setting_name)
        messages.append(
            checks.Error(
                f"{setting_value} is not a valid value for {setting_name}.",
                hint=hint,
                id="djstripe.E003",
            )
        )

    return messages


@checks.register("djstripe")
def check_webhook_event_callback_accepts_api_key(app_configs=None, **kwargs):
    """
    Checks if the custom callback accepts atleast 2 mandatory positional arguments
    """
    from inspect import signature

    from .settings import djstripe_settings

    messages = []

    # callable can have exactly 2 arguments or
    # if more than two, the rest need to be optional.
    callable = djstripe_settings.WEBHOOK_EVENT_CALLBACK

    if callable:
        # Deprecated in 2.8.0. Raise a warning.
        messages.append(
            checks.Warning(
                (
                    "DJSTRIPE_WEBHOOK_EVENT_CALLBACK is deprecated. See release notes"
                    " for details."
                ),
                hint=(
                    "If you need to trigger a function during webhook processing, "
                    "you can use djstripe.signals instead.\n"
                    "Available signals:\n"
                    "- djstripe.signals.webhook_pre_validate\n"
                    "- djstripe.signals.webhook_post_validate\n"
                    "- djstripe.signals.webhook_pre_process\n"
                    "- djstripe.signals.webhook_post_process\n"
                    "- djstripe.signals.webhook_processing_error"
                ),
            )
        )

        sig = signature(callable)
        signature_sz = len(sig.parameters.keys())

        if signature_sz < 2:
            messages.append(
                checks.Error(
                    f"{callable} accepts {signature_sz} arguments.",
                    hint=(
                        "You may have forgotten to add api_key parameter to your custom"
                        " callback."
                    ),
                    id="djstripe.E004",
                )
            )

    return messages
