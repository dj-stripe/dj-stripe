"""
dj-stripe Custom Field Definitions
"""
import decimal

from django.conf import SettingsReference, settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .settings import djstripe_settings
from .utils import convert_tstamp


def import_jsonfield():
    if djstripe_settings.USE_NATIVE_JSONFIELD:
        from django.db.models import JSONField as BaseJSONField
    else:
        from jsonfield import JSONField as BaseJSONField
    return BaseJSONField


class StripeForeignKey(models.ForeignKey):
    setting_name = "DJSTRIPE_FOREIGN_KEY_TO_FIELD"

    def __init__(self, *args, **kwargs):
        # The default value will only come into play if the check for
        # that setting has been disabled.
        kwargs["to_field"] = getattr(settings, self.setting_name, "id")
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["to_field"] = SettingsReference(
            getattr(settings, self.setting_name, "id"), self.setting_name
        )
        if "help_text" in kwargs:
            del kwargs["help_text"]
        return name, path, args, kwargs

    def get_default(self):
        # Override to bypass a weird bug in Django
        # https://stackoverflow.com/a/14390402/227443
        if isinstance(self.remote_field.model, str):
            return self._get_default()
        return super().get_default()


class PaymentMethodForeignKey(models.ForeignKey):
    def __init__(self, **kwargs):
        kwargs.setdefault("to", "DjstripePaymentMethod")
        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "help_text" in kwargs:
            del kwargs["help_text"]
        return name, path, args, kwargs


class StripePercentField(models.DecimalField):
    """A field used to define a percent according to djstripe logic."""

    def __init__(self, *args, **kwargs):
        """Assign default args to this field."""
        defaults = {
            "decimal_places": 2,
            "max_digits": 5,
            "validators": [MinValueValidator(1), MaxValueValidator(100)],
        }
        defaults.update(kwargs)
        super().__init__(*args, **defaults)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "help_text" in kwargs:
            del kwargs["help_text"]
        return name, path, args, kwargs


class StripeCurrencyCodeField(models.CharField):
    """
    A field used to store a three-letter currency code (eg. usd, eur, ...)
    """

    def __init__(self, *args, **kwargs):
        defaults = {"max_length": 3, "help_text": "Three-letter ISO currency code"}
        defaults.update(kwargs)
        super().__init__(*args, **defaults)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "help_text" in kwargs:
            del kwargs["help_text"]
        return name, path, args, kwargs


class StripeQuantumCurrencyAmountField(models.BigIntegerField):
    """
    A field used to store currency amounts in cents (etc) as per stripe.
    By contacting stripe support, some accounts will have their limit raised to 11
    digits, hence the use of BigIntegerField instead of IntegerField
    """

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "help_text" in kwargs:
            del kwargs["help_text"]
        return name, path, args, kwargs


class StripeDecimalCurrencyAmountField(models.DecimalField):
    """
    A legacy field to store currency amounts in dollars (etc).

    Stripe is always in cents. Historically djstripe stored everything in dollars.

    Note: Don't use this for new fields, use StripeQuantumCurrencyAmountField instead.
    We're planning on migrating existing fields in dj-stripe 3.0,
    see https://github.com/dj-stripe/dj-stripe/issues/955
    """

    def __init__(self, *args, **kwargs):
        """
        Assign default args to this field. By contacting stripe support, some accounts
        will have their limit raised to 11 digits
        """
        defaults = {"decimal_places": 2, "max_digits": 11}
        defaults.update(kwargs)
        super().__init__(*args, **defaults)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "help_text" in kwargs:
            del kwargs["help_text"]
        return name, path, args, kwargs

    def stripe_to_db(self, data):
        """Convert the raw value to decimal representation."""
        val = data.get(self.name)

        # If already a string, it's decimal in the API (eg. Prices).
        if isinstance(val, str):
            return decimal.Decimal(val)

        # Note: 0 is a possible return value, which is 'falseish'
        if val is not None:
            return val / decimal.Decimal("100")


class StripeEnumField(models.CharField):
    def __init__(self, enum, *args, **kwargs):
        self.enum = enum
        choices = enum.choices
        defaults = {"choices": choices, "max_length": max(len(k) for k, v in choices)}
        defaults.update(kwargs)
        super().__init__(*args, **defaults)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["enum"] = self.enum
        if "choices" in kwargs:
            del kwargs["choices"]
        if "help_text" in kwargs:
            del kwargs["help_text"]
        return name, path, args, kwargs


class StripeIdField(models.CharField):
    """A field with enough space to hold any stripe ID."""

    def __init__(self, *args, **kwargs):
        """
        Assign default args to this field.

        As per: https://stripe.com/docs/upgrades
        You can safely assume object IDs we generate will never exceed 255
        characters, but you should be able to handle IDs of up to that
        length.
        """
        defaults = {"max_length": 255, "blank": False, "null": False}
        defaults.update(kwargs)
        super().__init__(*args, **defaults)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "help_text" in kwargs:
            del kwargs["help_text"]
        return name, path, args, kwargs


class StripeDateTimeField(models.DateTimeField):
    """A field used to define a DateTimeField value according to djstripe logic."""

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "help_text" in kwargs:
            del kwargs["help_text"]
        return name, path, args, kwargs

    def stripe_to_db(self, data):
        """Convert the raw timestamp value to a DateTime representation."""
        val = data.get(self.name)

        # Note: 0 is a possible return value, which is 'falseish'
        if val is not None:
            return convert_tstamp(val)


class JSONField(import_jsonfield()):
    """A field used to define a JSONField value according to djstripe logic."""

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "help_text" in kwargs:
            del kwargs["help_text"]
        return name, path, args, kwargs
