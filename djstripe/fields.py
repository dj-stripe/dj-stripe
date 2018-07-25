"""
.. module:: djstripe.fields.

   :synopsis: dj-stripe Custom Field Definitions

.. moduleauthor:: Bill Huneke (@wahuneke)
"""
import decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .settings import USE_NATIVE_JSONFIELD
from .utils import convert_tstamp


if USE_NATIVE_JSONFIELD:
    from django.contrib.postgres.fields import JSONField as BaseJSONField
else:
    from jsonfield import JSONField as BaseJSONField


class PaymentMethodForeignKey(models.ForeignKey):
    def __init__(self, **kwargs):
        kwargs.setdefault("to", "PaymentMethod")
        super().__init__(**kwargs)


class StripeFieldMixin:
    """
    Custom fields for all Stripe data.
    """

    def stripe_to_db(self, data):
        """Convert stripe fields to defined database fields."""

        return data.get(self.name)


class StripeDecimalField(StripeFieldMixin, models.DecimalField):
    pass


class StripePercentField(StripeDecimalField):
    """A field used to define a percent according to djstripe logic."""

    def __init__(self, *args, **kwargs):
        """Assign default args to this field."""
        defaults = {
            'decimal_places': 2,
            'max_digits': 5,
            'validators': [MinValueValidator(1), MaxValueValidator(100)]
        }
        defaults.update(kwargs)
        super().__init__(*args, **defaults)


class StripeDecimalCurrencyAmountField(StripeDecimalField):
    """
    A field used to define currency according to djstripe logic.

    Stripe is always in cents. djstripe stores everything in dollars.
    """

    def __init__(self, *args, **kwargs):
        """Assign default args to this field."""
        defaults = {
            'decimal_places': 2,
            'max_digits': 8,
        }
        defaults.update(kwargs)
        super().__init__(*args, **defaults)

    def stripe_to_db(self, data):
        """Convert the raw value to decimal representation."""
        val = super().stripe_to_db(data)

        # Note: 0 is a possible return value, which is 'falseish'
        if val is not None:
            return val / decimal.Decimal("100")


class StripeCharField(StripeFieldMixin, models.CharField):
    """A field used to define a CharField value according to djstripe logic."""

    pass


class StripeEnumField(StripeCharField):
    def __init__(self, enum, *args, **kwargs):
        self.enum = enum
        choices = enum.choices
        defaults = {
            "choices": choices,
            "max_length": max(len(k) for k, v in choices)
        }
        defaults.update(kwargs)
        super().__init__(*args, **defaults)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["enum"] = self.enum
        del kwargs["choices"]
        return name, path, args, kwargs


class StripeIdField(StripeCharField):
    """A field with enough space to hold any stripe ID."""

    def __init__(self, *args, **kwargs):
        """
        Assign default args to this field.

        As per: https://stripe.com/docs/upgrades
        You can safely assume object IDs we generate will never exceed 255
        characters, but you should be able to handle IDs of up to that
        length.
        """
        defaults = {
            'max_length': 255,
            'blank': False,
            'null': False,
        }
        defaults.update(kwargs)
        super().__init__(*args, **defaults)


class StripeDateTimeField(StripeFieldMixin, models.DateTimeField):
    """A field used to define a DateTimeField value according to djstripe logic."""

    def stripe_to_db(self, data):
        """Convert the raw timestamp value to a DateTime representation."""
        val = super().stripe_to_db(data)

        # Note: 0 is a possible return value, which is 'falseish'
        if val is not None:
            return convert_tstamp(val)


class JSONField(StripeFieldMixin, BaseJSONField):
    """A field used to define a JSONField value according to djstripe logic."""

    pass
