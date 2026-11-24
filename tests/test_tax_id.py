"""
dj-stripe TaxId model tests
"""

import uuid
from copy import deepcopy
from unittest.mock import patch

import pytest
import stripe
from django.conf import settings
from django.test.testcases import TestCase

from djstripe import enums
from djstripe.models import TaxId
from djstripe.settings import djstripe_settings

from . import FAKE_CUSTOMER, FAKE_TAX_ID, AssertStripeFksMixin, StripeList
from .conftest import CreateAccountMixin

pytestmark = pytest.mark.django_db


class TestTaxIdStr(CreateAccountMixin, TestCase):
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve_tax_id",
        return_value=deepcopy(FAKE_TAX_ID),
        autospec=True,
    )
    def test___str__(
        self,
        tax_id_retrieve_mock,
        customer_retrieve_mock,
    ):
        tax_id = TaxId.sync_from_stripe_data(FAKE_TAX_ID)
        self.assertEqual(
            str(tax_id),
            f"{enums.TaxIdType.humanize(FAKE_TAX_ID['type'])} {FAKE_TAX_ID['value']}",
        )


class TestTransfer(CreateAccountMixin, AssertStripeFksMixin, TestCase):
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve_tax_id",
        return_value=deepcopy(FAKE_TAX_ID),
        autospec=True,
    )
    def test_sync_from_stripe_data(
        self,
        tax_id_retrieve_mock,
        customer_retrieve_mock,
    ):
        tax_id = TaxId.sync_from_stripe_data(FAKE_TAX_ID)
        assert tax_id
        assert tax_id.id == FAKE_TAX_ID["id"]
        assert tax_id.customer.id == FAKE_CUSTOMER["id"]
        self.assert_fks(
            tax_id,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
            },
        )

    @pytest.mark.stripe_api
    @pytest.mark.usefixtures("configure_settings")
    def test_api_list(self):
        stripe_customer = stripe.Customer.create(
            api_key=settings.STRIPE_SECRET_KEY,
            email=f"tax-id-api-list-{uuid.uuid4().hex}@example.com",
            metadata={"djstripe_test": "tax_id_api_list"},
        )
        try:
            tax_id = stripe.Customer.create_tax_id(
                stripe_customer.id,
                api_key=settings.STRIPE_SECRET_KEY,
                type="eu_vat",
                value="DE123456789",
            )

            tax_id_list = list(
                TaxId.api_list(
                    id=stripe_customer.id,
                    api_key=settings.STRIPE_SECRET_KEY,
                    limit=100,
                )
            )

            self.assertTrue(any(item.id == tax_id.id for item in tax_id_list))
        finally:
            stripe.Customer.delete(
                stripe_customer.id, api_key=settings.STRIPE_SECRET_KEY
            )


class TestTaxIdApiList(TestCase):
    @patch("stripe.TaxId.list", autospec=True)
    @patch("stripe.Customer.list_tax_ids", autospec=True)
    def test_api_list_lists_the_tax_ids_of_one_customer(
        self, list_tax_ids_mock, tax_id_list_mock
    ):
        # stripe.TaxId.list() rejects an `id` and, without an `owner`, lists
        # the account's own tax ids rather than a customer's.
        list_tax_ids_mock.return_value = StripeList(data=[])

        TaxId.api_list(id="cus_1", api_key="sk_test_x")

        tax_id_list_mock.assert_not_called()
        args, kwargs = list_tax_ids_mock.call_args
        # The customer id is a path parameter, which stripe-python 16+ only
        # accepts positionally.
        assert args == ("cus_1",)
        assert "id" not in kwargs
        assert kwargs["api_key"] == "sk_test_x"
        assert kwargs["stripe_version"] == djstripe_settings.STRIPE_API_VERSION
