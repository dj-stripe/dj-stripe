"""
.. module:: dj-stripe.tests.test_stripe_object
   :synopsis: dj-stripe StripeObject Model Tests.

.. moduleauthor:: Bill Huneke (@wahuneke)

"""

from django.test import TestCase

from djstripe.stripe_objects import StripeObject


class StripeObjectExceptionsTest(TestCase):
    def test_missing_apiname(self):
        # This class fails to provide a stripe_api_name attribute
        class MissingApiName(StripeObject):
            pass

        with self.assertRaises(NotImplementedError):
            MissingApiName.api()

    def test_missing_obj_to_record(self):
        # This class fails to provide a stripe_api_name attribute
        class MissingObjToRecord(StripeObject):
            stripe_api_name = "hello"

        with self.assertRaises(NotImplementedError):
            MissingObjToRecord.create_from_stripe_object({})

