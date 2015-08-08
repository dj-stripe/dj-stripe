"""
.. module:: dj-stripe.tests.test_context_managers
   :synopsis: dj-stripe Context Manager Tests.

.. moduleauthor:: Bill Huneke (@wahuneke)
.. moduleauthor:: Alex Kavanaugh (@akavanau)

"""

from django.test import TestCase

from djstripe.context_managers import stripe_temporary_api_version


class TestTemporaryVersion(TestCase):

    def test_basic(self):
        import stripe
        version = stripe.api_version

        with stripe_temporary_api_version("newversion"):
            self.assertEqual(stripe.api_version, "newversion")

        self.assertEqual(stripe.api_version, version)
