"""
.. module:: dj-stripe.tests.test_fields
   :synopsis: dj-stripe Custom Field Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Michael Thronhill (@mthornhill)

"""

from django.test.testcases import TestCase

from djstripe.fields import StripeTextField, StripeDateTimeField


class TestDeprecatedField(TestCase):
    deprecated = StripeTextField(deprecated=True)

    def test_stripe_to_db(self):
        self.deprecated.stripe_to_db(data="taco")


class TestDeprecatedDateTimeField(TestCase):
    deprecated = StripeDateTimeField(deprecated=True)

    def test_stripe_to_db(self):
        self.deprecated.stripe_to_db(data="salad")
