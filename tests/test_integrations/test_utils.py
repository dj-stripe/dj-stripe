"""
.. module:: dj-stripe.tests.test_integrations.test_utils
   :synopsis: dj-stripe Integrated Utilities Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from django.conf import settings
from django.test.testcases import TestCase

from djstripe.utils import get_supported_currency_choices

if settings.STRIPE_PUBLIC_KEY and settings.STRIPE_SECRET_KEY:
    class TestGetSupportedCurrencyChoices(TestCase):

        def test_get_choices(self):
            """
            Simple test to test sure that at least one currency choice tuple is returned.
            USD should always be an option.
            """

            currency_choices = get_supported_currency_choices(settings.STRIPE_SECRET_KEY)
            self.assertGreaterEqual(len(currency_choices), 1, "Currency choices pull returned an empty list.")
            self.assertEqual(tuple, type(currency_choices[0]), "Currency choices are not tuples.")
            self.assertIn(("usd", "USD"), currency_choices, "USD not in currency choices.")
