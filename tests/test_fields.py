"""
.. module:: dj-stripe.tests.test_fields
   :synopsis: dj-stripe Custom Field Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Michael Thronhill (@mthornhill)

"""
from django.test.testcases import TestCase

from djstripe.fields import StripeCurrencyField


class TestStripeCurrencyField(TestCase):
    noval = StripeCurrencyField(name="noval")

    def test_stripe_to_db_none_val(self):
        self.assertEqual(None, self.noval.stripe_to_db({"noval": None}))
