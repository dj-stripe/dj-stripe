"""
dj-stripe TaxCode Model Tests.
"""
from copy import deepcopy

import pytest
from django.test import TestCase

from djstripe.models import TaxCode
from tests import FAKE_TAX_CODE

pytestmark = pytest.mark.django_db


class TaxCodeTest(TestCase):
    def test_sync_from_stripe_data(self):
        tax_code = TaxCode.sync_from_stripe_data(deepcopy(FAKE_TAX_CODE))

        self.assertEqual(
            FAKE_TAX_CODE["id"],
            tax_code.id,
        )

    def test___str__(self):
        tax_code = TaxCode.sync_from_stripe_data(deepcopy(FAKE_TAX_CODE))

        self.assertEqual(
            "General - Tangible Goods: txcd_99999999",
            str(tax_code),
        )
