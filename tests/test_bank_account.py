"""
dj-stripe Bank Account Model Tests.
"""

from copy import deepcopy
from unittest.mock import patch

import pytest
import stripe
from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe import enums
from djstripe.exceptions import StripeObjectManipulationException
from djstripe.models import BankAccount

from . import (
    FAKE_BANK_ACCOUNT_IV,
    FAKE_BANK_ACCOUNT_SOURCE,
    FAKE_CUSTOM_ACCOUNT,
    FAKE_CUSTOMER_IV,
    FAKE_STANDARD_ACCOUNT,
    AssertStripeFksMixin,
)
from .conftest import CreateAccountMixin

pytestmark = pytest.mark.django_db


class TestStrBankAccount:
    @pytest.mark.parametrize(
        "fake_stripe_data, has_account",
        [
            (deepcopy(FAKE_BANK_ACCOUNT_IV), True),
            (deepcopy(FAKE_BANK_ACCOUNT_IV), False),
        ],
    )
    def test__str__(self, fake_stripe_data, has_account, monkeypatch):
        def mock_account_get(*args, **kwargs):
            return deepcopy(FAKE_CUSTOM_ACCOUNT)

        # monkeypatch stripe.Account.retrieve to return the desired json response.
        monkeypatch.setattr(stripe.Account, "retrieve", mock_account_get)

        bankaccount = BankAccount.sync_from_stripe_data(fake_stripe_data)

        if has_account:
            default = fake_stripe_data["default_for_currency"]
            assert (
                f"{fake_stripe_data['bank_name']} {fake_stripe_data['currency']} {'Default' if default else ''} {fake_stripe_data['routing_number']} {fake_stripe_data['last4']}"
                == str(bankaccount)
            )
        else:
            # ensure account does not exist
            fake_stripe_data_2 = deepcopy(fake_stripe_data)
            fake_stripe_data_2["account"] = None

            bankaccount = BankAccount.sync_from_stripe_data(fake_stripe_data_2)
            default = fake_stripe_data_2["default_for_currency"]
            assert (
                f"{fake_stripe_data_2['bank_name']} {fake_stripe_data_2['currency']} {'Default' if default else ''} {fake_stripe_data_2['routing_number']} {fake_stripe_data_2['last4']}"
                == str(bankaccount)
            )

    @pytest.mark.parametrize(
        "fake_stripe_data",
        [
            deepcopy(FAKE_BANK_ACCOUNT_IV),
            deepcopy(FAKE_BANK_ACCOUNT_SOURCE),
        ],
    )
    def test_human_readable_status(self, fake_stripe_data, monkeypatch):
        def mock_account_get(*args, **kwargs):
            return deepcopy(FAKE_CUSTOM_ACCOUNT)

        # monkeypatch stripe.Account.retrieve to return the desired json response.
        monkeypatch.setattr(stripe.Account, "retrieve", mock_account_get)

        bankaccount = BankAccount.sync_from_stripe_data(fake_stripe_data)

        if fake_stripe_data["status"] == "new":
            assert bankaccount.human_readable_status == "Pending Verification"
        else:
            assert (
                bankaccount.human_readable_status
                == enums.BankAccountStatus.humanize(fake_stripe_data["status"])
            )


class BankAccountTest(CreateAccountMixin, AssertStripeFksMixin, TestCase):
    def setUp(self):
        # create a Standard Stripe Account
        self.standard_account = FAKE_STANDARD_ACCOUNT.create()

        # create a Custom Stripe Account
        self.custom_account = FAKE_CUSTOM_ACCOUNT.create()

        user = get_user_model().objects.create_user(
            username="testuser", email="djstripe@example.com"
        )
        fake_empty_customer = deepcopy(FAKE_CUSTOMER_IV)
        fake_empty_customer["default_source"] = None
        fake_empty_customer["sources"] = []

        self.customer = fake_empty_customer.create_for_user(user)

    def test_attach_objects_hook_without_account(self):
        bank_account = BankAccount.sync_from_stripe_data(FAKE_BANK_ACCOUNT_SOURCE)
        self.assertEqual(bank_account.account, None)

    def test_create_bank_account_finds_account_with_customer_absent(self):
        FAKE_BANK_ACCOUNT_DICT = deepcopy(FAKE_BANK_ACCOUNT_SOURCE)
        FAKE_BANK_ACCOUNT_DICT["account"] = self.standard_account.id
        FAKE_BANK_ACCOUNT_DICT["customer"] = None

        bank_account = BankAccount.sync_from_stripe_data(FAKE_BANK_ACCOUNT_DICT)

        self.assertEqual(self.standard_account, bank_account.account)
        self.assertEqual(
            bank_account.get_stripe_dashboard_url(),
            f"https://dashboard.stripe.com/{bank_account.account.id}/settings/payouts",
        )

        self.assert_fks(
            bank_account,
            expected_blank_fks={
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.default_source",
                "djstripe.Customer.coupon",
            },
        )

    def test_api_call_no_account(self):
        exception_message = (
            "BankAccount objects must be manipulated through a Stripe Connected"
            " Account. Pass an Account object into this call."
        )

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            BankAccount._api_create()

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            BankAccount.api_list()

    def test_api_call_bad_account(self):
        exception_message = (
            "BankAccount objects must be manipulated through a Stripe Connected"
            " Account. Pass an Account object into this call."
        )

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            BankAccount._api_create(account="fish")

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            BankAccount.api_list(account="fish")

    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    def test__api_create_with_customer_absent(self, account_retrieve_mock):
        stripe_bank_account = BankAccount._api_create(
            account=self.custom_account, source=FAKE_BANK_ACCOUNT_IV["id"]
        )

        self.assertEqual(FAKE_BANK_ACCOUNT_IV, stripe_bank_account)

    @patch(
        "stripe.Account.delete_external_account",
        autospec=True,
    )
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    def test_delete_bankaccount_by_account(
        self,
        account_retrieve_mock,
        bank_account_delete_mock,
    ):
        stripe_bank_account = BankAccount._api_create(
            account=self.custom_account, source=FAKE_BANK_ACCOUNT_IV["id"]
        )
        bank_account = BankAccount.sync_from_stripe_data(stripe_bank_account)
        self.assertEqual(
            1, BankAccount.objects.filter(id=stripe_bank_account["id"]).count()
        )

        api_key = bank_account.default_api_key
        stripe_account = bank_account._get_stripe_account_id(api_key)

        assert bank_account.account is not None

        # delete BankAccount via the Stripe API
        bank_account._api_delete()

        bank_account_delete_mock.assert_called_once_with(
            self.custom_account.id,
            bank_account.id,
            api_key=api_key,
            stripe_account=stripe_account,
        )
