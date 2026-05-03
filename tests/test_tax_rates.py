"""
dj-stripe TaxRate Model Tests.
"""

from copy import deepcopy

import pytest
from django.test import TestCase

from djstripe.models import TaxRate
from tests import FAKE_TAX_RATE_EXAMPLE_1_VAT

from .conftest import CreateAccountMixin

pytestmark = pytest.mark.django_db


class TaxRateTest(CreateAccountMixin, TestCase):
    def test_sync_from_stripe_data(self):
        tax_rate = TaxRate.sync_from_stripe_data(deepcopy(FAKE_TAX_RATE_EXAMPLE_1_VAT))
        self.assertEqual(FAKE_TAX_RATE_EXAMPLE_1_VAT["id"], tax_rate.id)

    def test___str__(self):
        tax_rate = TaxRate.sync_from_stripe_data(deepcopy(FAKE_TAX_RATE_EXAMPLE_1_VAT))
        self.assertEqual(
            (
                f"{FAKE_TAX_RATE_EXAMPLE_1_VAT['display_name']} at"
                f" {FAKE_TAX_RATE_EXAMPLE_1_VAT['percentage']}%"
            ),
            str(tax_rate),
        )
