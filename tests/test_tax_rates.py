"""
dj-stripe SetupIntent Model Tests.
"""
from copy import deepcopy
from decimal import Decimal

from django.test import TestCase
from tests import (
    FAKE_TAX_RATE_EXAMPLE_1_VAT,
    FAKE_TAX_RATE_EXAMPLE_2_SALES,
    AssertStripeFksMixin,
)

from djstripe.models import TaxRate


class TaxRateTest(AssertStripeFksMixin, TestCase):
    def test_sync_from_stripe_data(self):
        tax_rate = TaxRate.sync_from_stripe_data(deepcopy(FAKE_TAX_RATE_EXAMPLE_1_VAT))
        # need to refresh to load percentage as decimal
        tax_rate.refresh_from_db()

        self.assertIsInstance(tax_rate.percentage, Decimal)
        self.assertEqual(tax_rate.percentage, Decimal("15.0"))

    def test_sync_from_stripe_data_non_integer(self):
        # an example non-integer taxrate
        tax_rate = TaxRate.sync_from_stripe_data(
            deepcopy(FAKE_TAX_RATE_EXAMPLE_2_SALES)
        )
        # need to refresh to load percentage as decimal
        tax_rate.refresh_from_db()

        self.assertIsInstance(tax_rate.percentage, Decimal)
        self.assertEqual(tax_rate.percentage, Decimal("4.25"))
