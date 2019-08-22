"""
dj-stripe Bank Account Model Tests.
"""

from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase

from djstripe.exceptions import StripeObjectManipulationException
from djstripe.models import BankAccount, Customer

from . import FAKE_BANK_ACCOUNT_SOURCE, FAKE_CUSTOMER_IV, AssertStripeFksMixin


class BankAccountTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        fake_empty_customer = deepcopy(FAKE_CUSTOMER_IV)
        fake_empty_customer["default_source"] = None
        fake_empty_customer["sources"] = []

        self.customer = Customer.sync_from_stripe_data(fake_empty_customer)

    def test_create_bank_account_finds_customer(self):
        bank_account = BankAccount.sync_from_stripe_data(
            deepcopy(FAKE_BANK_ACCOUNT_SOURCE)
        )

        self.assertEqual(self.customer, bank_account.customer)
        self.assertEqual(
            bank_account.get_stripe_dashboard_url(),
            self.customer.get_stripe_dashboard_url(),
        )

    def test_api_call_no_customer(self):
        exception_message = (
            "Bank Accounts must be manipulated through a Customer. "
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
            "Bank Accounts must be manipulated through a Customer. "
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
    def test_api_list(self, customer_retrieve_mock):
        bank_account_list = BankAccount.api_list(customer=self.customer)

        self.assertEqual([FAKE_BANK_ACCOUNT_SOURCE], bank_account_list)
