"""
dj-stripe TaxId Model Tests.
"""
from copy import deepcopy

from django.test import TestCase
from unittest.mock import patch
import pytest
from djstripe.exceptions import StripeObjectManipulationException

from djstripe.models import TaxId, Customer
from tests import (
    FAKE_TAX_ID,
    FAKE_CUSTOMER_WITH_TAX_ID,
    FAKE_CUSTOMER_WITHOUT_TAX_ID,
    AssertStripeFksMixin,
)


class TaxIdTest(AssertStripeFksMixin, TestCase):
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_WITHOUT_TAX_ID)
    )
    def test_sync_from_stripe_data(self, customer_mock):
        customer = Customer.sync_from_stripe_data(FAKE_CUSTOMER_WITHOUT_TAX_ID)
        self.assertEqual(customer.tax_ids.count(), 0)
        tax_id = TaxId.sync_from_stripe_data(deepcopy(FAKE_TAX_ID))
        self.assertEqual(tax_id.type, "eu_vat")
        self.assertEqual(tax_id.value, "DE123456789")
        self.assertEqual(customer.tax_ids.last(), tax_id)

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_WITH_TAX_ID))
    def test_api_list_success(self, customer_mock):
        customer = Customer.sync_from_stripe_data(customer_mock.return_value)
        self.assertEqual(customer.tax_ids.count(), 1)
        tax_ids = TaxId.api_list(customer=customer)
        self.assertEqual(customer.tax_ids.last().value, tax_ids["data"][0]["value"])

    def test_api_list_invalid(self):
        with pytest.raises(StripeObjectManipulationException) as e:
            TaxId.api_list(customer="Iamastring")
        assert (
            str(e.value)
            == "TaxIds must be manipulated through a Customer. Pass a Customer object into this call."
        )
