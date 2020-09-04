"""
dj-stripe System Checks
"""
import django
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
    Only used on Django < 3.1.
    """
    from . import settings as djstripe_settings

    messages = []
    error_msg = (
        "DJSTRIPE_USE_NATIVE_JSONFIELD is not compatible with engine {engine} "
        "for database {name}"
    )

    # This error check is skipped on Django 3.1+, because the native JSONField
    # will be used, which is compatible with mysql and sqlite.
    # https://docs.djangoproject.com/en/dev/releases/3.1/#postgresql-jsonfield
    if django.VERSION >= (3, 1):
        return messages

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
def check_native_jsonfield_set_on_recent_django_versions(app_configs=None, **kwargs):
    """
    Check that DJSTRIPE_USE_NATIVE_JSONFIELD is set on Django > 3.1.

    This is only a suggestion, as existing installations need a migration path.
    """

    messages = []

    # This error check is skipped on Django < 3.1+, because the native JSONField
    # was not available outside of Postgres engines then.
    if django.VERSION < (3, 1):
        return messages

    # NOTE: Not using app_settings.USE_NATIVE_JSONFIELD.
    # Only display this warning if the setting is unset.
    if not hasattr(settings, "DJSTRIPE_USE_NATIVE_JSONFIELD"):
        # TODO: Give more details on the migration path
        messages.append(
            checks.Warning(
                "DJSTRIPE_USE_NATIVE_JSONFIELD is not set.",
                hint=(
                    "On Django 3.1+, setting DJSTRIPE_USE_NATIVE_JSONFIELD = True is "
                    "recommended.\nPre-existing dj-stripe installations may require a "
                    "migration, in which case you may want to set it to False."
                ),
                id="djstripe.W005",
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


@checks.register("djstripe")
def check_djstripe_settings_foreign_key_to_field(app_configs=None, **kwargs):
    """
    Check that DJSTRIPE_FOREIGN_KEY_TO_FIELD is set to a valid value.
    """
    from django.conf import settings

    setting_name = "DJSTRIPE_FOREIGN_KEY_TO_FIELD"
    hint = (
        f'Set {setting_name} to "id" if this is a new installation, '
        f'otherwise set it to "djstripe_id".'
    )
    messages = []

    if not hasattr(settings, setting_name):
        messages.append(
            checks.Error(
                "%s is not set." % (setting_name),
                hint=hint,
                id="djstripe.E002",
            )
        )
    elif getattr(settings, setting_name) not in ("id", "djstripe_id"):
        messages.append(
            checks.Error(
                "%r is not a valid value for %s."
                % (getattr(settings, setting_name), setting_name),
                hint=hint,
                id="djstripe.E003",
            )
        )

    return messages
