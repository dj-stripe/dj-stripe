"""
dj-stripe ShippingRate Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.test import TestCase

from djstripe.models import ShippingRate
from tests import (
    FAKE_SHIPPING_RATE,
    FAKE_SHIPPING_RATE_WITH_TAX_CODE,
    FAKE_TAX_CODE,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


class ShippingRateTest(AssertStripeFksMixin, TestCase):
    def test_sync_from_stripe_data(self):
        shipping_rate = ShippingRate.sync_from_stripe_data(deepcopy(FAKE_SHIPPING_RATE))

        self.assertEqual(
            FAKE_SHIPPING_RATE["id"],
            shipping_rate.id,
        )

        self.assertEqual(
            FAKE_SHIPPING_RATE["tax_code"],
            None,
        )

        self.assert_fks(
            shipping_rate, expected_blank_fks={"djstripe.ShippingRate.tax_code"}
        )

    @patch(
        "stripe.TaxCode.retrieve", autospec=True, return_value=deepcopy(FAKE_TAX_CODE)
    )
    def test_sync_from_stripe_data_with_tax_code(self, tax_code_retrieve_mock):
        shipping_rate = ShippingRate.sync_from_stripe_data(
            deepcopy(FAKE_SHIPPING_RATE_WITH_TAX_CODE)
        )

        self.assertEqual(
            FAKE_SHIPPING_RATE["id"],
            shipping_rate.id,
        )

        self.assertEqual(
            FAKE_SHIPPING_RATE["tax_code"],
            None,
        )

        self.assert_fks(shipping_rate, expected_blank_fks={})

    def test___str__(self):
        shipping_rate = ShippingRate.sync_from_stripe_data(deepcopy(FAKE_SHIPPING_RATE))

        self.assertEqual(
            "Test Shipping Code with no Tax Code - $1.25 USD (Active)",
            str(shipping_rate),
        )
