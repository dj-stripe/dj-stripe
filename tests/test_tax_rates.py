"""
dj-stripe SetupIntent Model Tests.
"""
from copy import deepcopy
from decimal import Decimal

from django.test import TestCase

from djstripe.models import TaxRate
from tests import (
    FAKE_TAX_RATE_EXAMPLE_1_VAT,
    FAKE_TAX_RATE_EXAMPLE_2_SALES,
    AssertStripeFksMixin,
)


class TaxRateTest(AssertStripeFksMixin, TestCase):
    def test___str__(self):
        tax_rate = TaxRate.sync_from_stripe_data(deepcopy(FAKE_TAX_RATE_EXAMPLE_1_VAT))
        # need to refresh to load percentage as decimal
        tax_rate.refresh_from_db()

        self.assertEqual(
            f"{FAKE_TAX_RATE_EXAMPLE_1_VAT['display_name']} – {FAKE_TAX_RATE_EXAMPLE_1_VAT['jurisdiction']} at {FAKE_TAX_RATE_EXAMPLE_1_VAT['percentage']:.2f}%",
            str(tax_rate),
        )

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
