"""
.. module:: dj-stripe.tests.test_stripe_object
   :synopsis: dj-stripe StripeObject Model Tests.

.. moduleauthor:: Bill Huneke (@wahuneke)

"""

from django.test import TestCase

from mock import patch, PropertyMock

from djstripe.models import StripeObject


class StripeObjectTest(TestCase):
    def test_bad_impl(self):
        # This class fails to provide a stripe_api_name attribute
        class BadBad(StripeObject):
            pass

        with self.assertRaises(NotImplementedError):
            BadBad.api()

