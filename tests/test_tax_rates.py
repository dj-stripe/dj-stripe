"""
dj-stripe SetupIntent Model Tests.
"""
from copy import deepcopy
from decimal import Decimal

import pytest
from django.test import TestCase

from djstripe.models import TaxRate
from tests import FAKE_TAX_RATE_EXAMPLE_1_VAT, AssertStripeFksMixin

pytestmark = pytest.mark.django_db


class TaxRateTest(AssertStripeFksMixin, TestCase):
    def test___str__(self):
        tax_rate = TaxRate.sync_from_stripe_data(deepcopy(FAKE_TAX_RATE_EXAMPLE_1_VAT))
        # need to refresh to load percentage as decimal
        tax_rate.refresh_from_db()

        self.assertEqual(
            f"{FAKE_TAX_RATE_EXAMPLE_1_VAT['display_name']} – {FAKE_TAX_RATE_EXAMPLE_1_VAT['jurisdiction']} at {FAKE_TAX_RATE_EXAMPLE_1_VAT['percentage']:.4f}%",
            str(tax_rate),
        )


class TestTaxRateDecimal:
    @pytest.mark.parametrize(
        "inputted,expected",
        [
            (Decimal("1"), Decimal("1.0000")),
            (Decimal("1.5234567"), Decimal("1.5235")),
            (Decimal("0"), Decimal("0.0000")),
            (Decimal("23.2345678"), Decimal("23.2346")),
            ("1", Decimal("1.0000")),
            ("1.5234567", Decimal("1.5235")),
            ("0", Decimal("0.0000")),
            ("23.2345678", Decimal("23.2346")),
            (1, Decimal("1.0000")),
            (1.5234567, Decimal("1.5235")),
            (0, Decimal("0.0000")),
            (23.2345678, Decimal("23.2346")),
        ],
    )
    def test_decimal_tax_percent(self, inputted, expected):
        fake_tax_rate = deepcopy(FAKE_TAX_RATE_EXAMPLE_1_VAT)
        fake_tax_rate["percentage"] = inputted

        tax_rate = TaxRate.sync_from_stripe_data(fake_tax_rate)
        field_data = tax_rate.percentage

        assert isinstance(field_data, Decimal)
        assert field_data == expected
