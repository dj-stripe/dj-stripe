"""
dj-stripe TaxId model tests
"""
from copy import deepcopy
from unittest.mock import PropertyMock, patch

import pytest
from django.test.testcases import TestCase

from djstripe import enums
from djstripe.models import Customer, TaxId
from djstripe.settings import djstripe_settings

from . import FAKE_CUSTOMER, FAKE_TAX_ID, AssertStripeFksMixin

pytestmark = pytest.mark.django_db


class TestTaxIdStr(TestCase):
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
            f"{enums.TaxIdType.humanize(FAKE_TAX_ID['type'])} {FAKE_TAX_ID['value']} ({FAKE_TAX_ID['verification']['status']})",
        )


class TestTransfer(AssertStripeFksMixin, TestCase):
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
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
        )

    @patch(
        "stripe.Customer.list_tax_ids",
        autospec=True,
    )
    def test_api_list(
        self,
        tax_id_list_mock,
    ):
        p = PropertyMock(return_value=deepcopy(FAKE_TAX_ID))
        type(tax_id_list_mock).auto_paging_iter = p

        TaxId.api_list(id=FAKE_CUSTOMER["id"])

        tax_id_list_mock.assert_called_once_with(
            id=FAKE_CUSTOMER["id"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
        )
