"""
.. module:: dj-stripe.tests.test_fields
   :synopsis: dj-stripe Custom Field Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Michael Thronhill (@mthornhill)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from django.test.testcases import TestCase

from djstripe.fields import StripeCurrencyField, StripeDateTimeField, StripeTextField


class TestDeprecatedField(TestCase):
    deprecated = StripeTextField(deprecated=True)

    def test_stripe_to_db(self):
        self.assertEqual(None, self.deprecated.stripe_to_db(data="taco"))


class TestDeprecatedDateTimeField(TestCase):
    deprecated = StripeDateTimeField(deprecated=True)

    def test_stripe_to_db(self):
        self.assertEqual(None, self.deprecated.stripe_to_db(data="salad"))


class TestStripeCurrencyField(TestCase):
    noval = StripeCurrencyField(name="noval")

    def test_stripe_to_db_none_val(self):
        self.assertEqual(None, self.noval.stripe_to_db({"noval": None}))
