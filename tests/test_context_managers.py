"""
.. module:: dj-stripe.tests.test_context_managers
   :synopsis: dj-stripe Context Manager Tests.

.. moduleauthor:: Bill Huneke (@wahuneke)
.. moduleauthor:: Alex Kavanaugh (@akavanau)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import stripe
from django.test import TestCase

from djstripe.context_managers import stripe_temporary_api_version


class TestTemporaryVersion(TestCase):

    def test_basic_with_exception(self):
        version = stripe.api_version

        with self.assertRaises(ValueError):
            with stripe_temporary_api_version('2016-03-07'):
                self.assertEqual(stripe.api_version, '2016-03-07')
                raise ValueError('Something happened')

        self.assertEqual(stripe.api_version, version)

    def test_basic_without_validation(self):
        version = stripe.api_version

        with stripe_temporary_api_version('newversion', validate=False):
            self.assertEqual(stripe.api_version, 'newversion')

        self.assertEqual(stripe.api_version, version)
