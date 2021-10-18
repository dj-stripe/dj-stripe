"""
dj-stripe TransferReversal model tests
"""
from copy import deepcopy
from unittest.mock import PropertyMock, patch

import pytest
from django.test.testcases import TestCase

from djstripe.models import TransferReversal
from djstripe.models.connect import Transfer
from djstripe.settings import djstripe_settings

from . import (
    FAKE_BALANCE_TRANSACTION_II,
    FAKE_STANDARD_ACCOUNT,
    FAKE_TRANSFER,
    FAKE_TRANSFER_WITH_1_REVERSAL,
    IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


class TestTransferReversalStr:
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION_II),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve_reversal",
        autospec=True,
        return_value=deepcopy(FAKE_TRANSFER_WITH_1_REVERSAL),
    )
    def test___str__(
        self,
        transfer_reversal_retrieve_mock,
        balance_transaction_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):

        transfer_reversal = TransferReversal.sync_from_stripe_data(
            deepcopy(FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0])
        )
        assert str(f"{transfer_reversal.transfer}") == str(transfer_reversal)


class TestTransfer(AssertStripeFksMixin, TestCase):
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION_II),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve_reversal",
        autospec=True,
        return_value=deepcopy(FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0]),
    )
    def test_sync_from_stripe_data(
        self,
        transfer_reversal_retrieve_mock,
        balance_transaction_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):

        transfer_reversal = TransferReversal.sync_from_stripe_data(
            deepcopy(FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0])
        )

        balance_transaction_retrieve_mock.assert_not_called()
        transfer_reversal_retrieve_mock.assert_not_called()

        assert (
            transfer_reversal.balance_transaction.id
            == FAKE_TRANSFER["balance_transaction"]["id"]
        )
        assert (
            transfer_reversal.transfer.id
            == FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0]["transfer"]["id"]
        )

        self.assert_fks(transfer_reversal, expected_blank_fks="")

    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION_II),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve_reversal",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
        return_value=deepcopy(FAKE_TRANSFER_WITH_1_REVERSAL),
    )
    def test_api_retrieve(
        self,
        transfer_reversal_retrieve_mock,
        balance_transaction_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):

        transfer_reversal = TransferReversal.sync_from_stripe_data(
            deepcopy(FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0])
        )
        transfer_reversal.api_retrieve()

        transfer_reversal_retrieve_mock.assert_called_once_with(
            id=FAKE_TRANSFER_WITH_1_REVERSAL["id"],
            nested_id=FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0]["id"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            expand=["balance_transaction", "transfer"],
            stripe_account=transfer_reversal.djstripe_owner_account.id,
        )

    @patch.object(Transfer, "_attach_objects_post_save_hook")
    # we are returning any value for the Transfer.objects.get as we only need to avoid the Transfer.DoesNotExist error
    @patch(
        "djstripe.models.connect.Transfer.objects.get",
        return_value=deepcopy(FAKE_TRANSFER),
    )
    @patch(
        "stripe.Transfer.create_reversal",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
        return_value=deepcopy(FAKE_TRANSFER_WITH_1_REVERSAL),
    )
    def test__api_create(
        self,
        transfer_reversal_create_mock,
        transfer_get_mock,
        transfer__attach_object_post_save_hook_mock,
    ):

        TransferReversal._api_create(
            id=FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0]["transfer"]["id"]
        )

        transfer_reversal_create_mock.assert_called_once_with(
            id=FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0]["transfer"]["id"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
        )

    @patch(
        "stripe.Transfer.list_reversals", autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED
    )
    def test_api_list(self, transfer_reversal_list_mock):
        p = PropertyMock(return_value=deepcopy(FAKE_TRANSFER_WITH_1_REVERSAL))
        type(transfer_reversal_list_mock).auto_paging_iter = p

        TransferReversal.api_list(
            id=FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0]["transfer"]["id"]
        )

        transfer_reversal_list_mock.assert_called_once_with(
            id=FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0]["transfer"]["id"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
        )

    def test_is_valid_object(self):
        assert TransferReversal.is_valid_object(
            deepcopy(FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0])
        )
