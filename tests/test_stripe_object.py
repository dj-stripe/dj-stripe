"""
.. module:: dj-stripe.tests.test_stripe_object
   :synopsis: dj-stripe StripeObject Model Tests.

.. moduleauthor:: Bill Huneke (@wahuneke)

"""

from django.core.exceptions import ImproperlyConfigured, FieldError

from django.test import TestCase

from djstripe.stripe_objects import StripeObject, StripeCharField, StripeBooleanField


SIMPLE_OBJ = {'id': 'yo', 'livemode': True}
SIMPLE_OBJ_RESULT = {'stripe_id': 'yo', 'description': None, 'livemode': True, 'metadata': None, 'stripe_timestamp': None}


class StripeObjectExceptionsTest(TestCase):
    def test_missing_apiname(self):
        # This class fails to provide a stripe_api_name attribute
        class MissingApiName(StripeObject):
            pass

        with self.assertRaises(NotImplementedError):
            MissingApiName._api()

    def test_deprecated_boolean(self):
        with self.assertRaises(ImproperlyConfigured):
            class DeprecatedBool(StripeObject):
                bad = StripeBooleanField(deprecated=True)

    def test_missing_required_field(self):
        class HasRequiredField(StripeObject):
            im_not_optional = StripeCharField()

        with self.assertRaises(FieldError):
            HasRequiredField._stripe_object_to_record(SIMPLE_OBJ)

    def test_missing_nonrequired_field(self):
        class HasRequiredField(StripeObject):
            im_not_optional = StripeCharField(stripe_required=False)

        # Should be no exception here
        obj = HasRequiredField._stripe_object_to_record(SIMPLE_OBJ)
        self.assertEqual(obj['im_not_optional'], None)


class StripeObjectBasicTest(TestCase):
    def test_basic_val_to_db(self):
        # Instantiate a stripeobject model class
        class BasicModel(StripeObject):
            stripe_api_name = "hello"

        result = BasicModel._stripe_object_to_record(SIMPLE_OBJ)
        self.assertEqual(result, SIMPLE_OBJ_RESULT)
