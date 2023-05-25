"""
dj-stripe Payout Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe.models import BankAccount, Card, Payout

from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_BANK_ACCOUNT,
    FAKE_CARD,
    FAKE_CUSTOM_ACCOUNT,
    FAKE_CUSTOMER,
    FAKE_EXPRESS_ACCOUNT,
    FAKE_PAYOUT_CUSTOM_BANK_ACCOUNT,
    FAKE_PAYOUT_CUSTOM_CARD,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_STANDARD_ACCOUNT,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


# todo add tests for Payout reverse once python client supports that
# https://stripe.com/docs/api/payouts/reverse
class TestPayout(AssertStripeFksMixin, TestCase):
    def setUp(self):
        # create a Standard Stripe Account
        self.standard_account = FAKE_STANDARD_ACCOUNT.create()

        # create a Custom Stripe Account
        self.custom_account = FAKE_CUSTOM_ACCOUNT.create()

        # create an Express Stripe Account
        self.express_account = FAKE_EXPRESS_ACCOUNT.create()

        user = get_user_model().objects.create_user(
            username="arnav13", email="arnav13@gmail.com"
        )
        fake_empty_customer = deepcopy(FAKE_CUSTOMER)
        fake_empty_customer["default_source"] = None
        fake_empty_customer["sources"] = []

        self.customer = fake_empty_customer.create_for_user(user)

        self.card = Card.sync_from_stripe_data(FAKE_CARD)
        self.bank_account = BankAccount.sync_from_stripe_data(FAKE_BANK_ACCOUNT)

    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch.object(
        BankAccount,
        "api_retrieve",
        return_value=deepcopy(FAKE_BANK_ACCOUNT),
        autospec=True,
    )
    @patch.object(
        Card,
        "api_retrieve",
        return_value=deepcopy(FAKE_BANK_ACCOUNT),
        autospec=True,
    )
    def test_sync_from_stripe_data(
        self,
        card_retrieve_mock,
        bank_account_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_payout_custom = deepcopy(FAKE_PAYOUT_CUSTOM_BANK_ACCOUNT)
        payout = Payout.sync_from_stripe_data(fake_payout_custom)

        self.assertEqual(payout.balance_transaction.id, FAKE_BALANCE_TRANSACTION["id"])
        self.assertEqual(payout.destination.id, fake_payout_custom["destination"])
        self.assertEqual(payout.djstripe_owner_account.id, FAKE_PLATFORM_ACCOUNT["id"])
        self.assert_fks(
            payout,
            expected_blank_fks={
                "djstripe.Payout.failure_balance_transaction",
                "djstripe.Payout.original_payout",
                "djstripe.Payout.reversed_by",
                "djstripe.Payout.payout (related name)",
                "djstripe.Payout.reversed_payout (related name)",
                "djstripe.BankAccount.account",
                "djstripe.BankAccount.customer",
            },
        )

        fake_payout_express = deepcopy(FAKE_PAYOUT_CUSTOM_CARD)
        payout = Payout.sync_from_stripe_data(fake_payout_express)

        self.assertEqual(payout.balance_transaction.id, FAKE_BALANCE_TRANSACTION["id"])
        self.assertEqual(payout.destination.id, fake_payout_express["destination"])
        self.assertEqual(payout.djstripe_owner_account.id, FAKE_PLATFORM_ACCOUNT["id"])
        self.assert_fks(
            payout,
            expected_blank_fks={
                "djstripe.Payout.failure_balance_transaction",
                "djstripe.Payout.original_payout",
                "djstripe.Payout.reversed_by",
                "djstripe.Payout.payout (related name)",
                "djstripe.Payout.reversed_payout (related name)",
                "djstripe.BankAccount.account",
                "djstripe.BankAccount.customer",
            },
        )

    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch.object(
        BankAccount,
        "api_retrieve",
        return_value=deepcopy(FAKE_BANK_ACCOUNT),
        autospec=True,
    )
    @patch.object(
        Card,
        "api_retrieve",
        return_value=deepcopy(FAKE_BANK_ACCOUNT),
        autospec=True,
    )
    def test___str__(
        self,
        card_retrieve_mock,
        bank_account_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_payout_custom = deepcopy(FAKE_PAYOUT_CUSTOM_BANK_ACCOUNT)
        payout = Payout.sync_from_stripe_data(fake_payout_custom)

        self.assertEqual(str(payout), "10 (Paid)")

        fake_payout_express = deepcopy(FAKE_PAYOUT_CUSTOM_CARD)
        payout = Payout.sync_from_stripe_data(fake_payout_express)

        self.assertEqual(str(payout), "10 (Paid)")
