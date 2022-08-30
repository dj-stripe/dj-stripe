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
        assert tax_code
        assert tax_code.id == FAKE_TAX_CODE["id"]

    def test___str__(self):
        tax_code = TaxCode.sync_from_stripe_data(deepcopy(FAKE_TAX_CODE))
        assert str(tax_code) == "General - Tangible Goods: txcd_99999999"
