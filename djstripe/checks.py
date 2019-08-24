"""
dj-stripe System Checks
"""
from django.conf import settings
from django.core import checks
from django.utils.dateparse import date_re


@checks.register("djstripe")
def check_stripe_api_key(app_configs=None, **kwargs):
    """Check the user has configured API live/test keys correctly."""
    from . import settings as djstripe_settings

    messages = []

    if not djstripe_settings.STRIPE_SECRET_KEY:
        msg = "Could not find a Stripe API key."
        hint = "Add STRIPE_TEST_SECRET_KEY and STRIPE_LIVE_SECRET_KEY to your settings."
        messages.append(checks.Critical(msg, hint=hint, id="djstripe.C001"))
    elif djstripe_settings.STRIPE_LIVE_MODE:
        if not djstripe_settings.LIVE_API_KEY.startswith(("sk_live_", "rk_live_")):
            msg = "Bad Stripe live API key."
            hint = 'STRIPE_LIVE_SECRET_KEY should start with "sk_live_"'
            messages.append(checks.Critical(msg, hint=hint, id="djstripe.C002"))
    else:
        if not djstripe_settings.TEST_API_KEY.startswith(("sk_test_", "rk_test_")):
            msg = "Bad Stripe test API key."
            hint = 'STRIPE_TEST_SECRET_KEY should start with "sk_test_"'
            messages.append(checks.Critical(msg, hint=hint, id="djstripe.C003"))

    return messages


def validate_stripe_api_version(version):
    """
    Check the API version is formatted correctly for Stripe.

    The expected format is an iso8601 date: `YYYY-MM-DD`

    :param version: The version to set for the Stripe API.
    :type version: ``str``
    :returns bool: Whether the version is formatted correctly.
    """
    return date_re.match(version)


@checks.register("djstripe")
def check_stripe_api_version(app_configs=None, **kwargs):
    """Check the user has configured API version correctly."""
    from . import settings as djstripe_settings

    messages = []
    default_version = djstripe_settings.DEFAULT_STRIPE_API_VERSION
    version = djstripe_settings.get_stripe_api_version()

    if not validate_stripe_api_version(version):
        msg = "Invalid Stripe API version: {}".format(version)
        hint = "STRIPE_API_VERSION should be formatted as: YYYY-MM-DD"
        messages.append(checks.Critical(msg, hint=hint, id="djstripe.C004"))

    if version != default_version:
        msg = (
            "The Stripe API version has a non-default value of '{}'. "
            "Non-default versions are not explicitly supported, and may "
            "cause compatibility issues.".format(version)
        )
        hint = "Use the dj-stripe default for Stripe API version: {}".format(
            default_version
        )
        messages.append(checks.Warning(msg, hint=hint, id="djstripe.W001"))

    return messages


@checks.register("djstripe")
def check_native_jsonfield_postgres_engine(app_configs=None, **kwargs):
    """
    Check that the DJSTRIPE_USE_NATIVE_JSONFIELD isn't set unless Postgres is in use.
    """
    from . import settings as djstripe_settings

    messages = []
    error_msg = (
        "DJSTRIPE_USE_NATIVE_JSONFIELD is not compatible with engine {engine} "
        "for database {name}"
    )

    if djstripe_settings.USE_NATIVE_JSONFIELD:
        for db_name, db_config in settings.DATABASES.items():
            # Hi there.
            # You may be reading this because you are using Postgres, but
            # dj-stripe is not detecting that correctly. For example, maybe you
            # are using multiple databases with different engines, or you have
            # your own backend. As long as you are certain you can support jsonb,
            # you can use the SILENCED_SYSTEM_CHECKS setting to ignore this check.
            engine = db_config.get("ENGINE", "")
            if "postgresql" not in engine and "postgis" not in engine:
                messages.append(
                    checks.Critical(
                        error_msg.format(name=repr(db_name), engine=repr(engine)),
                        hint="Switch to Postgres, or unset "
                        "DJSTRIPE_USE_NATIVE_JSONFIELD",
                        id="djstripe.C005",
                    )
                )

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
                "STRIPE_API_HOST should not be set in production! "
                "This is most likely unintended.",
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
    from . import settings as djstripe_settings

    messages = []

    secret = djstripe_settings.WEBHOOK_SECRET
    if secret and not secret.startswith("whsec_"):
        messages.append(
            checks.Warning(
                "DJSTRIPE_WEBHOOK_SECRET does not look valid",
                hint="It should start with whsec_...",
                id="djstripe.W003",
            )
        )

    return messages


@checks.register("djstripe")
def check_webhook_validation(app_configs=None, **kwargs):
    """
    Check that DJSTRIPE_WEBHOOK_VALIDATION is valid
    """
    from . import settings as djstripe_settings

    messages = []

    validation_options = ("verify_signature", "retrieve_event")

    if djstripe_settings.WEBHOOK_VALIDATION is None:
        messages.append(
            checks.Warning(
                "Webhook validation is disabled, this is a security risk if the "
                "webhook view is enabled",
                hint="Set DJSTRIPE_WEBHOOK_VALIDATION to one of {}".format(
                    ", ".join(validation_options)
                ),
                id="djstripe.W004",
            )
        )
    elif djstripe_settings.WEBHOOK_VALIDATION == "verify_signature":
        if not djstripe_settings.WEBHOOK_SECRET:
            messages.append(
                checks.Critical(
                    "DJSTRIPE_WEBHOOK_VALIDATION='verify_signature' "
                    "but DJSTRIPE_WEBHOOK_SECRET is not set",
                    hint="Set DJSTRIPE_WEBHOOK_SECRET or set "
                    "DJSTRIPE_WEBHOOK_VALIDATION='retrieve_event'",
                    id="djstripe.C006",
                )
            )
    elif djstripe_settings.WEBHOOK_VALIDATION not in validation_options:
        messages.append(
            checks.Critical(
                "DJSTRIPE_WEBHOOK_VALIDATION is invalid",
                hint="Set DJSTRIPE_WEBHOOK_VALIDATION to one of {} or None".format(
                    ", ".join(validation_options)
                ),
                id="djstripe.C007",
            )
        )

    return messages


@checks.register("djstripe")
def check_subscriber_key_length(app_configs=None, **kwargs):
    """
    Check that DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY fits in metadata.

    Docs: https://stripe.com/docs/api#metadata
    """
    from . import settings as djstripe_settings

    messages = []

    key = djstripe_settings.SUBSCRIBER_CUSTOMER_KEY
    key_size = len(str(key))
    if key and key_size > 40:
        messages.append(
            checks.Error(
                "DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY must be no more than "
                "40 characters long",
                hint="Current value: %r (%i characters)" % (key, key_size),
                id="djstripe.E001",
            )
        )

    return messages
