"""
.. module:: dj-stripe.tests.test_stripe_object
   :synopsis: dj-stripe StripeObject Model Tests.

.. moduleauthor:: Bill Huneke (@wahuneke)

"""
from django.test import TestCase

from djstripe.models import Customer, StripeObject


class StripeObjectExceptionsTest(TestCase):
    def test_no_object_value(self):
        # Instantiate a stripeobject model class
        class BasicModel(StripeObject):
            pass

        with self.assertRaises(ValueError):
            # Errors because there's no object value
            BasicModel._stripe_object_to_record({
                "id": "test_XXXXXXXX",
                "livemode": False,
            })

    def test_bad_object_value(self):
        with self.assertRaises(ValueError):
            # Errors because the object is not correct
            Customer._stripe_object_to_record({
                "id": "test_XXXXXXXX",
                "livemode": False,
                "object": "not_a_customer",
            })
