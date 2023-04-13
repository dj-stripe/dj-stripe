"""
dj-stripe TransferReversal model tests
"""
from copy import deepcopy
from unittest.mock import PropertyMock, patch

import pytest
from django.test.testcases import TestCase

from djstripe.models import Transfer, TransferReversal
from djstripe.models.base import IdempotencyKey
from djstripe.settings import djstripe_settings

from . import (
    FAKE_BALANCE_TRANSACTION_II,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_TRANSFER,
    FAKE_TRANSFER_WITH_1_REVERSAL,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


class TestTransferReversalStr(TestCase):
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
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
        self.assertEqual(str(f"{transfer_reversal.transfer}"), str(transfer_reversal))


class TestTransfer(AssertStripeFksMixin, TestCase):
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
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
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
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
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
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
        autospec=True,
        return_value=deepcopy(FAKE_TRANSFER_WITH_1_REVERSAL),
    )
    def test__api_create(
        self,
        transfer_reversal_create_mock,
        transfer_get_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        reversal_obj_id = FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0][
            "transfer"
        ]["id"]
        TransferReversal._api_create(id=reversal_obj_id)

        # Get just created IdempotencyKey
        idempotency_key = IdempotencyKey.objects.get(
            action=f"transferreversal:create:{reversal_obj_id}",
            livemode=False,
        )
        idempotency_key = str(idempotency_key.uuid)

        transfer_reversal_create_mock.assert_called_once_with(
            id=FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0]["transfer"]["id"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
            idempotency_key=idempotency_key,
            metadata={"idempotency_key": idempotency_key},
        )

    @patch("stripe.Transfer.list_reversals", autospec=True)
    def test_api_list(self, transfer_reversal_list_mock):
        p = PropertyMock(return_value=deepcopy(FAKE_TRANSFER_WITH_1_REVERSAL))
        type(transfer_reversal_list_mock).auto_paging_iter = p

        TransferReversal.api_list(
            id=FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0]["transfer"]["id"]
        )

        transfer_reversal_list_mock.assert_called_once_with(
            id=FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0]["transfer"]["id"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
        )

    def test_is_valid_object(self):
        assert TransferReversal.is_valid_object(
            deepcopy(FAKE_TRANSFER_WITH_1_REVERSAL["reversals"]["data"][0])
        )
