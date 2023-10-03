"""
dj-stripe Dispute model tests
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test.testcases import TestCase

from djstripe.models import Dispute
from djstripe.settings import djstripe_settings

from . import (
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CUSTOMER,
    FAKE_DISPUTE_BALANCE_TRANSACTION,
    FAKE_DISPUTE_CHARGE,
    FAKE_DISPUTE_I,
    FAKE_DISPUTE_III,
    FAKE_DISPUTE_PAYMENT_INTENT,
    FAKE_FILEUPLOAD_ICON,
)

pytestmark = pytest.mark.django_db
from .conftest import CreateAccountMixin


class TestDispute(CreateAccountMixin, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="fake_customer_1", email=FAKE_CUSTOMER["email"]
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_PAYMENT_INTENT),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_CHARGE),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Dispute.retrieve", return_value=deepcopy(FAKE_DISPUTE_I), autospec=True
    )
    def test___str__(
        self,
        dispute_retrieve_mock,
        file_retrieve_mock,
        balance_transaction_retrieve_mock,
        charge_retrieve_mock,
        payment_intent_retrieve_mock,
        payment_method_retrieve_mock,
    ):
        dispute = Dispute.sync_from_stripe_data(FAKE_DISPUTE_I)
        self.assertEqual(str(dispute), "$10.00 USD (Needs response) ")

    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_PAYMENT_INTENT),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_CHARGE),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Dispute.retrieve", return_value=deepcopy(FAKE_DISPUTE_I), autospec=True
    )
    def test_sync_from_stripe_data(
        self,
        dispute_retrieve_mock,
        file_retrieve_mock,
        balance_transaction_retrieve_mock,
        charge_retrieve_mock,
        payment_intent_retrieve_mock,
        payment_method_retrieve_mock,
    ):
        dispute = Dispute.sync_from_stripe_data(FAKE_DISPUTE_I)
        assert dispute.id == FAKE_DISPUTE_I["id"]

    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_PAYMENT_INTENT),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_CHARGE),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Dispute.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_III),
        autospec=True,
    )
    def test__attach_objects_post_save_hook(
        self,
        dispute_retrieve_mock,
        file_retrieve_mock,
        balance_transaction_retrieve_mock,
        charge_retrieve_mock,
        payment_intent_retrieve_mock,
        payment_method_retrieve_mock,
    ):
        dispute = Dispute.sync_from_stripe_data(FAKE_DISPUTE_III)
        assert dispute.id == FAKE_DISPUTE_III["id"]

        # assert File was retrieved correctly
        file_retrieve_mock.assert_called_once_with(
            id=FAKE_DISPUTE_III["evidence"]["receipt"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            expand=[],
            stripe_account=None,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
        )

        # assert Balance Transactions were retrieved correctly
        balance_transaction_retrieve_mock.assert_called_once_with(
            id=FAKE_DISPUTE_BALANCE_TRANSACTION["id"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
            expand=[],
            stripe_account=None,
        )

    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_PAYMENT_INTENT),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_CHARGE),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_DISPUTE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Dispute.retrieve", return_value=deepcopy(FAKE_DISPUTE_I), autospec=True
    )
    def test_get_stripe_dashboard_url(
        self,
        dispute_retrieve_mock,
        file_retrieve_mock,
        balance_transaction_retrieve_mock,
        charge_retrieve_mock,
        payment_intent_retrieve_mock,
        payment_method_retrieve_mock,
    ):
        dispute = Dispute.sync_from_stripe_data(FAKE_DISPUTE_I)
        self.assertEqual(
            dispute.get_stripe_dashboard_url(),
            (
                f"{dispute._get_base_stripe_dashboard_url()}"
                f"{dispute.stripe_dashboard_item_name}/{dispute.payment_intent.id}"
            ),
        )
