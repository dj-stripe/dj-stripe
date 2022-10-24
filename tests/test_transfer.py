"""
dj-stripe Transfer model tests
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.test.testcases import TestCase

from djstripe.models import Transfer

from . import (
    FAKE_BALANCE_TRANSACTION_II,
    FAKE_STANDARD_ACCOUNT,
    FAKE_TRANSFER,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


def FAKE_TRANSFER_COMPLETE_REVERSAL():
    data = deepcopy(FAKE_TRANSFER)
    data["reversed"] = True
    data["amount_reversed"] = data["amount"]
    return data


def FAKE_TRANSFER_PARTIAL_REVERSAL():
    data = deepcopy(FAKE_TRANSFER)
    assert data["amount"] > 1
    data["amount_reversed"] = data["amount"] - 1
    return data


class TestTransferStr:
    @pytest.mark.parametrize(
        "fake_transfer_data",
        [
            deepcopy(FAKE_TRANSFER),
            FAKE_TRANSFER_COMPLETE_REVERSAL(),
            FAKE_TRANSFER_PARTIAL_REVERSAL(),
        ],
    )
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION_II),
        autospec=True,
    )
    @patch("stripe.Transfer.retrieve", autospec=True)
    def test___str__(
        self,
        transfer_retrieve_mock,
        balance_transaction_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
        fake_transfer_data,
    ):

        transfer_retrieve_mock.return_value = fake_transfer_data
        transfer = Transfer.sync_from_stripe_data(fake_transfer_data)

        if fake_transfer_data["reversed"]:
            assert "$1.00 USD Reversed" == str(transfer)

        elif fake_transfer_data["amount_reversed"]:
            assert "$1.00 USD Partially Reversed" == str(transfer)

        else:
            assert "$1.00 USD" == str(transfer)


class TestTransfer(AssertStripeFksMixin, TestCase):
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION_II),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    def test_sync_from_stripe_data(
        self,
        transfer_retrieve_mock,
        balance_transaction_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):

        transfer = Transfer.sync_from_stripe_data(deepcopy(FAKE_TRANSFER))

        balance_transaction_retrieve_mock.assert_not_called()
        transfer_retrieve_mock.assert_not_called()

        assert (
            transfer.balance_transaction.id
            == FAKE_TRANSFER["balance_transaction"]["id"]
        )
        # assert transfer.destination.id == FAKE_TRANSFER["destination"]
        assert transfer.destination == FAKE_TRANSFER["destination"]

        self.assert_fks(transfer, expected_blank_fks="")

    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION_II),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    def test_fee(
        self,
        transfer_retrieve_mock,
        balance_transaction_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):

        transfer = Transfer.sync_from_stripe_data(deepcopy(FAKE_TRANSFER))
        assert transfer.fee == FAKE_BALANCE_TRANSACTION_II["fee"]
        assert transfer.fee == transfer.balance_transaction.fee

    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION_II),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    def test_get_stripe_dashboard_url(
        self,
        transfer_retrieve_mock,
        balance_transaction_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):

        transfer = Transfer.sync_from_stripe_data(deepcopy(FAKE_TRANSFER))

        assert transfer.get_stripe_dashboard_url() == (
            f"{transfer._get_base_stripe_dashboard_url()}"
            f"connect/{transfer.stripe_dashboard_item_name}/{transfer.id}"
        )
