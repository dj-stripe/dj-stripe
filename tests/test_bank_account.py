"""
dj-stripe Bank Account Model Tests.
"""

from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe.exceptions import StripeObjectManipulationException
from djstripe.models import BankAccount

from . import (
    FAKE_BANK_ACCOUNT_SOURCE,
    FAKE_CUSTOMER_IV,
    AssertStripeFksMixin,
    default_account,
)


class BankAccountTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        self.account = default_account()
        self.user = get_user_model().objects.create_user(
            username="testuser", email="djstripe@example.com"
        )
        fake_empty_customer = deepcopy(FAKE_CUSTOMER_IV)
        fake_empty_customer["default_source"] = None
        fake_empty_customer["sources"] = []

        self.customer = fake_empty_customer.create_for_user(self.user)

    def test_create_bank_account_finds_customer(self):
        bank_account = BankAccount.sync_from_stripe_data(
            deepcopy(FAKE_BANK_ACCOUNT_SOURCE)
        )

        self.assertEqual(self.customer, bank_account.customer)
        self.assertEqual(
            bank_account.get_stripe_dashboard_url(),
            self.customer.get_stripe_dashboard_url(),
        )

        self.assert_fks(
            bank_account,
            expected_blank_fks={
                "djstripe.BankAccount.account",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.default_source",
                "djstripe.Customer.coupon",
            },
        )

    def test_api_call_no_customer(self):
        exception_message = (
            "BankAccounts must be manipulated through a Customer. "
            "Pass a Customer object into this call."
        )

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            BankAccount._api_create()

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            BankAccount.api_list()

    def test_api_call_bad_customer(self):
        exception_message = (
            "BankAccounts must be manipulated through a Customer. "
            "Pass a Customer object into this call."
        )

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            BankAccount._api_create(customer="fish")

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            BankAccount.api_list(customer="fish")

    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_IV),
        autospec=True,
    )
    def test_api_create(self, customer_retrieve_mock):
        stripe_bank_account = BankAccount._api_create(
            customer=self.customer, source=FAKE_BANK_ACCOUNT_SOURCE["id"]
        )

        self.assertEqual(FAKE_BANK_ACCOUNT_SOURCE, stripe_bank_account)

    @patch("tests.BankAccountDict.delete", autospec=True)
    @patch(
        "stripe.BankAccount.retrieve",
        return_value=deepcopy(FAKE_BANK_ACCOUNT_SOURCE),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_IV),
        autospec=True,
    )
    def test_remove(
        self,
        customer_retrieve_mock,
        bank_account_retrieve_mock,
        bank_account_delete_mock,
    ):
        stripe_bank_account = BankAccount._api_create(
            customer=self.customer, source=FAKE_BANK_ACCOUNT_SOURCE["id"]
        )
        BankAccount.sync_from_stripe_data(stripe_bank_account)

        self.assertEqual(1, self.customer.bank_account.count())

        bank_account = self.customer.bank_account.all()[0]
        bank_account.remove()

        self.assertEqual(0, self.customer.bank_account.count())
        self.assertTrue(bank_account_delete_mock.called)

    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_IV),
        autospec=True,
    )
    def test_remove_already_deleted_card(self, customer_retrieve_mock):
        stripe_bank_account = BankAccount._api_create(
            customer=self.customer, source=FAKE_BANK_ACCOUNT_SOURCE["id"]
        )
        BankAccount.sync_from_stripe_data(stripe_bank_account)

        self.assertEqual(self.customer.bank_account.count(), 1)
        bank_account_object = self.customer.bank_account.first()
        BankAccount.objects.filter(id=stripe_bank_account["id"]).delete()
        self.assertEqual(self.customer.bank_account.count(), 0)
        bank_account_object.remove()
        self.assertEqual(self.customer.bank_account.count(), 0)

    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_IV),
        autospec=True,
    )
    def test_api_list(self, customer_retrieve_mock):
        bank_account_list = BankAccount.api_list(customer=self.customer)

        self.assertEqual([FAKE_BANK_ACCOUNT_SOURCE], [i for i in bank_account_list])
