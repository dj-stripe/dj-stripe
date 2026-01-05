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
from djstripe.models import Customer, TaxId
from djstripe.settings import djstripe_settings

from . import FAKE_CUSTOMER, FAKE_TAX_ID, AssertStripeFksMixin
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
            (
                f"{enums.TaxIdType.humanize(FAKE_TAX_ID['type'])} {FAKE_TAX_ID['value']} ({FAKE_TAX_ID['verification']['status']})"
            ),
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

    # we are returning any value for the Customer.objects.get as we only need to avoid the Customer.DoesNotExist error
    @patch(
        "djstripe.models.core.Customer.objects.get",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "stripe.Customer.create_tax_id",
        return_value=deepcopy(FAKE_TAX_ID),
        autospec=True,
    )
    def test__api_create(
        self,
        tax_id_create_mock,
        customer_get_mock,
    ):
        STRIPE_DATA = TaxId._api_create(
            id=FAKE_CUSTOMER["id"], type=FAKE_TAX_ID["type"], value=FAKE_TAX_ID["value"]
        )

        assert STRIPE_DATA == FAKE_TAX_ID
        tax_id_create_mock.assert_called_once_with(
            id=FAKE_CUSTOMER["id"],
            type=FAKE_TAX_ID["type"],
            value=FAKE_TAX_ID["value"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
        )

    # we are returning any value for the Customer.objects.get as we only need to avoid the Customer.DoesNotExist error
    @patch(
        "djstripe.models.core.Customer.objects.get",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "stripe.Customer.create_tax_id",
        return_value=deepcopy(FAKE_TAX_ID),
        autospec=True,
    )
    def test__api_create_no_id_kwarg(
        self,
        tax_id_create_mock,
        customer_get_mock,
    ):
        with pytest.raises(KeyError) as exc:
            TaxId._api_create(
                FAKE_CUSTOMER["id"],
                type=FAKE_TAX_ID["type"],
                value=FAKE_TAX_ID["value"],
            )
        assert "Customer Object ID is missing" in str(exc.value)

    @patch(
        "stripe.Customer.create_tax_id",
        return_value=deepcopy(FAKE_TAX_ID),
        autospec=True,
    )
    def test__api_create_no_customer(
        self,
        tax_id_create_mock,
    ):
        with pytest.raises(Customer.DoesNotExist):
            TaxId._api_create(
                id=FAKE_CUSTOMER["id"],
                type=FAKE_TAX_ID["type"],
                value=FAKE_TAX_ID["value"],
            )

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
    def test_api_retrieve(
        self,
        tax_id_retrieve_mock,
        customer_retrieve_mock,
    ):
        tax_id = TaxId.sync_from_stripe_data(FAKE_TAX_ID)
        assert tax_id
        tax_id.api_retrieve()
        assert tax_id.djstripe_owner_account

        tax_id_retrieve_mock.assert_called_once_with(
            id=FAKE_CUSTOMER["id"],
            nested_id=FAKE_TAX_ID["id"],
            expand=[],
            stripe_account=tax_id.djstripe_owner_account.id,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
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
