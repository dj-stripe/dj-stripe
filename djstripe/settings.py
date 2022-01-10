"""
dj-stripe settings
"""
import stripe
from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from .checks import validate_stripe_api_version


class DjstripeSettings:
    """Container for Dj-stripe settings

    :return: Initialised settings for Dj-stripe.
    :rtype: object

    """

    DEFAULT_STRIPE_API_VERSION = "2020-08-27"

    ZERO_DECIMAL_CURRENCIES = set(
        [
            "bif",
            "clp",
            "djf",
            "gnf",
            "jpy",
            "kmf",
            "krw",
            "mga",
            "pyg",
            "rwf",
            "vnd",
            "vuv",
            "xaf",
            "xof",
            "xpf",
        ]
    )

    def __init__(self):
        # Set STRIPE_API_HOST if you want to use a different Stripe API server
        # Example: https://github.com/stripe/stripe-mock
        if hasattr(settings, "STRIPE_API_HOST"):
            stripe.api_base = getattr(settings, "STRIPE_API_HOST")

    # generic setter and deleter methods to ensure object patching works
    def __setattr__(self, name, value):
        self.__dict__[name] = value

    def __delattr__(self, name):
        del self.__dict__[name]

    @property
    def SUBSCRIPTION_REDIRECT(self):
        return getattr(settings, "DJSTRIPE_SUBSCRIPTION_REDIRECT", "")

    @property
    def SUBSCRIPTION_REQUIRED_EXCEPTION_URLS(self):
        return getattr(settings, "DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS", ())

    @property
    def subscriber_request_callback(self):
        return self.get_callback_function(
            "DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK",
            default=(lambda request: request.user),
        )

    @property
    def get_idempotency_key(self):
        return self.get_callback_function(
            "DJSTRIPE_IDEMPOTENCY_KEY_CALLBACK", self._get_idempotency_key
        )

    @property
    def USE_NATIVE_JSONFIELD(self):
        return getattr(settings, "DJSTRIPE_USE_NATIVE_JSONFIELD", True)

    @property
    def PRORATION_POLICY(self):
        return getattr(settings, "DJSTRIPE_PRORATION_POLICY", None)

    @property
    def DJSTRIPE_WEBHOOK_URL(self):
        return getattr(settings, "DJSTRIPE_WEBHOOK_URL", r"^webhook/$")

    @property
    def WEBHOOK_TOLERANCE(self):
        return getattr(
            settings, "DJSTRIPE_WEBHOOK_TOLERANCE", stripe.Webhook.DEFAULT_TOLERANCE
        )

    @property
    def WEBHOOK_VALIDATION(self):
        return getattr(settings, "DJSTRIPE_WEBHOOK_VALIDATION", "verify_signature")

    @property
    def WEBHOOK_SECRET(self):
        return getattr(settings, "DJSTRIPE_WEBHOOK_SECRET", "")

    # Webhook event callbacks allow an application to take control of what happens
    # when an event from Stripe is received.  One suggestion is to put the event
    # onto a task queue (such as celery) for asynchronous processing.
    @property
    def WEBHOOK_EVENT_CALLBACK(self):
        return self.get_callback_function("DJSTRIPE_WEBHOOK_EVENT_CALLBACK")

    @property
    def SUBSCRIBER_CUSTOMER_KEY(self):
        return getattr(
            settings, "DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY", "djstripe_subscriber"
        )

    @property
    def TEST_API_KEY(self):
        return getattr(settings, "STRIPE_TEST_SECRET_KEY", "")

    @property
    def LIVE_API_KEY(self):
        return getattr(settings, "STRIPE_LIVE_SECRET_KEY", "")

    # Determines whether we are in live mode or test mode
    @property
    def STRIPE_LIVE_MODE(self):
        return getattr(settings, "STRIPE_LIVE_MODE", False)

    @property
    def STRIPE_SECRET_KEY(self):
        # Default secret key
        if hasattr(settings, "STRIPE_SECRET_KEY"):
            STRIPE_SECRET_KEY = settings.STRIPE_SECRET_KEY
        else:
            STRIPE_SECRET_KEY = (
                self.LIVE_API_KEY if self.STRIPE_LIVE_MODE else self.TEST_API_KEY
            )
        return STRIPE_SECRET_KEY

    @property
    def STRIPE_PUBLIC_KEY(self):
        # Default public key
        if hasattr(settings, "STRIPE_PUBLIC_KEY"):
            STRIPE_PUBLIC_KEY = settings.STRIPE_PUBLIC_KEY
        elif self.STRIPE_LIVE_MODE:
            STRIPE_PUBLIC_KEY = getattr(settings, "STRIPE_LIVE_PUBLIC_KEY", "")
        else:
            STRIPE_PUBLIC_KEY = getattr(settings, "STRIPE_TEST_PUBLIC_KEY", "")
        return STRIPE_PUBLIC_KEY

    @property
    def STRIPE_API_VERSION(self) -> str:
        """
        Get the desired API version to use for Stripe requests.
        """
        version = getattr(settings, "STRIPE_API_VERSION", stripe.api_version)
        return version or self.DEFAULT_STRIPE_API_VERSION

    def get_callback_function(self, setting_name, default=None):
        """
        Resolve a callback function based on a setting name.

        If the setting value isn't set, default is returned.  If the setting value
        is already a callable function, that value is used - If the setting value
        is a string, an attempt is made to import it.  Anything else will result in
        a failed import causing ImportError to be raised.

        :param setting_name: The name of the setting to resolve a callback from.
        :type setting_name: string (``str``/``unicode``)
        :param default: The default to return if setting isn't populated.
        :type default: ``bool``
        :returns: The resolved callback function (if any).
        :type: ``callable``
        """
        func = getattr(settings, setting_name, None)
        if not func:
            return default

        if callable(func):
            return func

        if isinstance(func, str):
            func = import_string(func)

        if not callable(func):
            raise ImproperlyConfigured(
                "{name} must be callable.".format(name=setting_name)
            )

        return func

    def _get_idempotency_key(self, object_type, action, livemode) -> str:
        from .models import IdempotencyKey

        action = "{}:{}".format(object_type, action)
        idempotency_key, _created = IdempotencyKey.objects.get_or_create(
            action=action, livemode=livemode
        )
        return str(idempotency_key.uuid)

    def get_default_api_key(self, livemode) -> str:
        """
        Returns the default API key for a value of `livemode`.
        """
        if livemode is None:
            # Livemode is unknown. Use the default secret key.
            return self.STRIPE_SECRET_KEY
        elif livemode:
            # Livemode is true, use the live secret key
            return self.LIVE_API_KEY or self.STRIPE_SECRET_KEY
        else:
            # Livemode is false, use the test secret key
            return self.TEST_API_KEY or self.STRIPE_SECRET_KEY

    def get_subscriber_model_string(self) -> str:
        """Get the configured subscriber model as a module path string."""
        return getattr(settings, "DJSTRIPE_SUBSCRIBER_MODEL", settings.AUTH_USER_MODEL)  # type: ignore

    def get_subscriber_model(self):
        """
        Attempt to pull settings.DJSTRIPE_SUBSCRIBER_MODEL.

        Users have the option of specifying a custom subscriber model via the
        DJSTRIPE_SUBSCRIBER_MODEL setting.

        This methods falls back to AUTH_USER_MODEL if DJSTRIPE_SUBSCRIBER_MODEL is not set.

        Returns the subscriber model that is active in this project.
        """
        model_name = self.get_subscriber_model_string()

        # Attempt a Django 1.7 app lookup
        try:
            subscriber_model = django_apps.get_model(model_name)
        except ValueError:
            raise ImproperlyConfigured(
                "DJSTRIPE_SUBSCRIBER_MODEL must be of the form 'app_label.model_name'."
            )
        except LookupError:
            raise ImproperlyConfigured(
                "DJSTRIPE_SUBSCRIBER_MODEL refers to model '{model}' "
                "that has not been installed.".format(model=model_name)
            )

        if (
            "email"
            not in [field_.name for field_ in subscriber_model._meta.get_fields()]
        ) and not hasattr(subscriber_model, "email"):
            raise ImproperlyConfigured(
                "DJSTRIPE_SUBSCRIBER_MODEL must have an email attribute."
            )

        if model_name != settings.AUTH_USER_MODEL:
            # Custom user model detected. Make sure the callback is configured.
            func = self.get_callback_function(
                "DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK"
            )
            if not func:
                raise ImproperlyConfigured(
                    "DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK must be implemented "
                    "if a DJSTRIPE_SUBSCRIBER_MODEL is defined."
                )

        return subscriber_model

    def set_stripe_api_version(self, version=None, validate=True):
        """
        Set the desired API version to use for Stripe requests.

        :param version: The version to set for the Stripe API.
        :type version: ``str``
        :param validate: If True validate the value for the specified version).
        :type validate: ``bool``
        """
        version = version or self.STRIPE_API_VERSION

        if validate:
            valid = validate_stripe_api_version(version)
            if not valid:
                raise ValueError("Bad stripe API version: {}".format(version))

        stripe.api_version = version


# initialise the settings object
djstripe_settings = DjstripeSettings()
