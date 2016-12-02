# -*- coding: utf-8 -*-
"""
.. module:: djstripe.fields.

   :synopsis: dj-stripe Custom Field Definitions

.. moduleauthor:: Bill Huneke (@wahuneke)
"""

import decimal

from django.core.exceptions import ImproperlyConfigured, FieldError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from jsonfield import JSONField

from .utils import dict_nested_accessor, convert_tstamp


class StripeFieldMixin(object):
    """
    Custom fields for all Stripe data.

    This allows keeping track of which database fields are suitable for
    sending to or receiving from Stripe. Also, allows a few handy extra parameters.
    """

    # Used if the name at stripe is different from the name in our database
    # Include a . in name if value is nested in dict in Stripe's object
    # (e.g.  stripe_name = "data.id"  -->  obj["data"]["id"])
    stripe_name = None

    # If stripe_name is None, this can also be used to specify a nested value, but
    # the final value is assumed to be the database field name
    # (e.g.    nested_name = "data"    -->  obj["data"][db_field_name]
    nested_name = None

    # This indicates that this field will always appear in a stripe object. It will be
    # an Exception if we try to parse a stripe object that does not include this field
    # in the data. If set to False then null=True attribute will be automatically set
    stripe_required = True

    # If a field was populated in previous API versions but we don't want to drop the old
    # data for some reason, mark it as deprecated. This will make sure we never try to send
    # it to Stripe or expect in Stripe data received
    # This setting automatically implies Null=True
    deprecated = False

    def __init__(self, *args, **kwargs):
        """
        Assign class instance variables based on kwargs.

        Assign extra class instance variables if stripe_required is defined or
        if deprecated is defined.
        """
        self.stripe_name = kwargs.pop('stripe_name', self.stripe_name)
        self.nested_name = kwargs.pop('nested_name', self.nested_name)
        self.stripe_required = kwargs.pop('stripe_required', self.stripe_required)
        self.deprecated = kwargs.pop('deprecated', self.deprecated)
        if not self.stripe_required:
            kwargs["null"] = True

        if self.deprecated:
            kwargs["null"] = True
            kwargs["default"] = None
        super(StripeFieldMixin, self).__init__(*args, **kwargs)

    def stripe_to_db(self, data):
        """Try converting stripe fields to defined database fields."""
        if not self.deprecated:
            try:
                if self.stripe_name:
                    result = dict_nested_accessor(data, self.stripe_name)
                elif self.nested_name:
                    result = dict_nested_accessor(data, self.nested_name + "." + self.name)
                else:
                    result = data[self.name]
            except (KeyError, TypeError):
                if self.stripe_required:
                    model_name = self.model._meta.object_name if hasattr(self, "model") else ""
                    raise FieldError("Required stripe field '{field_name}' was not"
                                     " provided in {model_name} data object.".format(field_name=self.name,
                                                                                     model_name=model_name))
                else:
                    result = None

            return result


class StripePercentField(StripeFieldMixin, models.DecimalField):
    """A field used to define a percent according to djstripe logic."""

    def __init__(self, *args, **kwargs):
        """Assign default args to this field."""
        defaults = {
            'decimal_places': 2,
            'max_digits': 5,
            'validators': [MinValueValidator(1.00), MaxValueValidator(100.00)]
        }
        defaults.update(kwargs)
        super(StripePercentField, self).__init__(*args, **defaults)


class StripeCurrencyField(StripeFieldMixin, models.DecimalField):
    """
    A field used to define currency according to djstripe logic.

    Stripe is always in cents. djstripe stores everything in dollars.
    """

    def __init__(self, *args, **kwargs):
        """Assign default args to this field."""
        defaults = {
            'decimal_places': 2,
            'max_digits': 7,
        }
        defaults.update(kwargs)
        super(StripeCurrencyField, self).__init__(*args, **defaults)

    def stripe_to_db(self, data):
        """Convert the raw value to decimal representation."""
        val = super(StripeCurrencyField, self).stripe_to_db(data)

        # Note: 0 is a possible return value, which is 'falseish'
        if val is not None:
            return val / decimal.Decimal("100")


class StripeBooleanField(StripeFieldMixin, models.BooleanField):
    """A field used to define a boolean value according to djstripe logic."""

    def __init__(self, *args, **kwargs):
        """Throw an error when a user tries to deprecate."""
        if kwargs.get("deprecated", False):
            raise ImproperlyConfigured("Boolean field cannot be deprecated. Change field type to "
                                       "StripeNullBooleanField")
        super(StripeBooleanField, self).__init__(*args, **kwargs)


class StripeNullBooleanField(StripeFieldMixin, models.NullBooleanField):
    """A field used to define a NullBooleanField value according to djstripe logic."""

    pass


class StripeCharField(StripeFieldMixin, models.CharField):
    """A field used to define a CharField value according to djstripe logic."""

    pass


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
        super(StripeIdField, self).__init__(*args, **defaults)


class StripeTextField(StripeFieldMixin, models.TextField):
    """A field used to define a TextField value according to djstripe logic."""

    pass


class StripeDateTimeField(StripeFieldMixin, models.DateTimeField):
    """A field used to define a DateTimeField value according to djstripe logic."""

    def stripe_to_db(self, data):
        """Convert the raw timestamp value to a DateTime representation."""
        val = super(StripeDateTimeField, self).stripe_to_db(data)

        # Note: 0 is a possible return value, which is 'falseish'
        if val is not None:
            return convert_tstamp(val)


class StripeIntegerField(StripeFieldMixin, models.IntegerField):
    """A field used to define a IntegerField value according to djstripe logic."""

    pass


class StripeJSONField(StripeFieldMixin, JSONField):
    """A field used to define a JSONField value according to djstripe logic."""

    pass
