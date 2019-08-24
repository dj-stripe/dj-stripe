"""
dj-stripe Custom Field Tests.
"""
from django.test.testcases import TestCase

from djstripe.fields import StripeDecimalCurrencyAmountField


class TestStripeCurrencyField(TestCase):
    noval = StripeDecimalCurrencyAmountField(name="noval")

    def test_stripe_to_db_none_val(self):
        self.assertEqual(None, self.noval.stripe_to_db({"noval": None}))
