"""
dj-stripe Custom Field Definitions
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


class StripeCurrencyCodeField(models.CharField):
	"""
	A field used to store a three-letter currency code (eg. usd, eur, ...)
	"""

	def __init__(self, *args, **kwargs):
		defaults = {"max_length": 3, "help_text": "Three-letter ISO currency code"}
		defaults.update(kwargs)
		super().__init__(*args, **defaults)


class StripeQuantumCurrencyAmountField(models.IntegerField):
	pass


class StripeDecimalCurrencyAmountField(models.DecimalField):
	"""
	A field used to define currency according to djstripe logic.

	Stripe is always in cents. djstripe stores everything in dollars.
	"""

	def __init__(self, *args, **kwargs):
		"""Assign default args to this field."""
		defaults = {"decimal_places": 2, "max_digits": 8}
		defaults.update(kwargs)
		super().__init__(*args, **defaults)

	def stripe_to_db(self, data):
		"""Convert the raw value to decimal representation."""
		val = data.get(self.name)

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
		del kwargs["choices"]
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


class StripeDateTimeField(models.DateTimeField):
	"""A field used to define a DateTimeField value according to djstripe logic."""

	def stripe_to_db(self, data):
		"""Convert the raw timestamp value to a DateTime representation."""
		val = data.get(self.name)

		# Note: 0 is a possible return value, which is 'falseish'
		if val is not None:
			return convert_tstamp(val)


class JSONField(BaseJSONField):
	"""A field used to define a JSONField value according to djstripe logic."""

	pass
