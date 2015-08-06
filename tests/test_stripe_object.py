"""
.. module:: dj-stripe.tests.test_stripe_object
   :synopsis: dj-stripe StripeObject Model Tests.

.. moduleauthor:: Bill Huneke (@wahuneke)

"""

from django.test import TestCase

from mock import patch, PropertyMock

from djstripe.stripe_objects import StripeObject


class StripeObjectExceptionsTest(TestCase):
    def test_missing_apiname(self):
        # This class fails to provide a stripe_api_name attribute
        class MissingApiName(StripeObject):
            pass

        with self.assertRaises(NotImplementedError):
            MissingApiName.api()


class StripeObjectBasicTest(TestCase):
    def test_basic_val_to_db(self):
        # Instantiate a stripeobject model class
        class BasicModel(StripeObject):
            stripe_api_name = "hello"

        result = BasicModel.stripe_obj_to_record({'id': 1, 'livemode': False})
        self.assertEqual(result, {'stripe_id': 1, 'livemode': False})
