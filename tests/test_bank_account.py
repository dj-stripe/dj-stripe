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
    FAKE_BANK_ACCOUNT_IV,
    FAKE_BANK_ACCOUNT_SOURCE,
    FAKE_CUSTOM_ACCOUNT,
    FAKE_CUSTOMER_IV,
    FAKE_STANDARD_ACCOUNT,
    AssertStripeFksMixin,
)


class BankAccountTest(AssertStripeFksMixin, TestCase):
    def setUp(self):

        # create a Standard Stripe Account
        self.account = FAKE_STANDARD_ACCOUNT.create()

        user = get_user_model().objects.create_user(
            username="testuser", email="djstripe@example.com"
        )
        fake_empty_customer = deepcopy(FAKE_CUSTOMER_IV)
        fake_empty_customer["default_source"] = None
        fake_empty_customer["sources"] = []

        self.customer = fake_empty_customer.create_for_user(user)

    def test_attach_objects_hook_without_customer(self):
        FAKE_BANK_ACCOUNT_DICT = deepcopy(FAKE_BANK_ACCOUNT_SOURCE)
        FAKE_BANK_ACCOUNT_DICT["customer"] = None

        bank_account = BankAccount.sync_from_stripe_data(FAKE_BANK_ACCOUNT_DICT)
        self.assertEqual(bank_account.customer, None)

    def test_attach_objects_hook_without_account(self):
        bank_account = BankAccount.sync_from_stripe_data(FAKE_BANK_ACCOUNT_SOURCE)
        self.assertEqual(bank_account.account, None)

    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_IV),
        autospec=True,
    )
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    def test_api_retrieve_by_customer_equals_retrieval_by_account(
        self, account_retrieve_mock, customer_retrieve_mock
    ):
        # deepcopy the BankAccount object
        FAKE_BANK_ACCOUNT_DICT = deepcopy(FAKE_BANK_ACCOUNT_IV)

        bankaccount = BankAccount.sync_from_stripe_data(FAKE_BANK_ACCOUNT_DICT)
        bankaccount_by_customer = bankaccount.api_retrieve()

        # Add account
        FAKE_BANK_ACCOUNT_DICT["account"] = self.account.id
        FAKE_BANK_ACCOUNT_DICT["customer"] = None

        bankaccount = BankAccount.sync_from_stripe_data(FAKE_BANK_ACCOUNT_DICT)
        bankaccount_by_account = bankaccount.api_retrieve()

        # assert the same bankaccount object gets retrieved
        self.assertCountEqual(bankaccount_by_customer, bankaccount_by_account)

    def test_create_bank_account_finds_customer_with_account_absent(self):
        bank_account = BankAccount.sync_from_stripe_data(FAKE_BANK_ACCOUNT_SOURCE)

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

    def test_create_bank_account_finds_customer_with_account_present(self):
        FAKE_BANK_ACCOUNT_DICT = deepcopy(FAKE_BANK_ACCOUNT_SOURCE)
        FAKE_BANK_ACCOUNT_DICT["account"] = self.account.id

        bank_account = BankAccount.sync_from_stripe_data(FAKE_BANK_ACCOUNT_DICT)

        self.assertEqual(self.customer, bank_account.customer)
        self.assertEqual(self.account, bank_account.account)
        self.assertEqual(
            bank_account.get_stripe_dashboard_url(),
            self.customer.get_stripe_dashboard_url(),
        )

        self.assert_fks(
            bank_account,
            expected_blank_fks={
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.default_source",
                "djstripe.Customer.coupon",
            },
        )

    def test_create_bank_account_finds_account_with_customer_absent(self):
        FAKE_BANK_ACCOUNT_DICT = deepcopy(FAKE_BANK_ACCOUNT_SOURCE)
        FAKE_BANK_ACCOUNT_DICT["account"] = self.account.id
        FAKE_BANK_ACCOUNT_DICT["customer"] = None

        bank_account = BankAccount.sync_from_stripe_data(FAKE_BANK_ACCOUNT_DICT)

        self.assertEqual(self.account, bank_account.account)
        self.assertEqual(
            bank_account.get_stripe_dashboard_url(),
            self.account.get_stripe_dashboard_url(),
        )

        self.assert_fks(
            bank_account,
            expected_blank_fks={
                "djstripe.BankAccount.customer",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.default_source",
                "djstripe.Customer.coupon",
            },
        )

    def test_api_call_no_customer_and_no_account(self):
        exception_message = (
            "BankAccounts must be manipulated through either a Stripe Connected Account or a customer. "
            "Pass a Customer or an Account object into this call."
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

    def test_api_call_bad_account(self):
        exception_message = (
            "BankAccounts must be manipulated through a Stripe Connected Account. "
            "Pass an Account object into this call."
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
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_IV),
        autospec=True,
    )
    def test__api_create_with_account_absent(self, customer_retrieve_mock):
        stripe_bank_account = BankAccount._api_create(
            customer=self.customer, source=FAKE_BANK_ACCOUNT_SOURCE["id"]
        )

        self.assertEqual(FAKE_BANK_ACCOUNT_SOURCE, stripe_bank_account)

    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_IV),
        autospec=True,
    )
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    def test__api_create_with_customer_and_account(
        self, account_retrieve_mock, customer_retrieve_mock
    ):

        FAKE_BANK_ACCOUNT_DICT = deepcopy(FAKE_BANK_ACCOUNT_SOURCE)
        FAKE_BANK_ACCOUNT_DICT["account"] = self.account.id

        stripe_bank_account = BankAccount._api_create(
            account=self.account,
            customer=self.customer,
            source=FAKE_BANK_ACCOUNT_DICT["id"],
        )

        self.assertEqual(FAKE_BANK_ACCOUNT_SOURCE, stripe_bank_account)

    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_IV),
        autospec=True,
    )
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    def test__api_create_with_customer_absent(
        self, account_retrieve_mock, customer_retrieve_mock
    ):
        stripe_bank_account = BankAccount._api_create(
            account=self.account, source=FAKE_BANK_ACCOUNT_IV["id"]
        )

        self.assertEqual(FAKE_BANK_ACCOUNT_IV, stripe_bank_account)

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
    def test_remove_bankaccount_by_customer(
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
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    def test_remove_bankaccount_by_account(
        self,
        account_retrieve_mock,
    ):
        stripe_bank_account = BankAccount._api_create(
            account=self.account, source=FAKE_BANK_ACCOUNT_IV["id"]
        )
        BankAccount.sync_from_stripe_data(stripe_bank_account)

        # remove BankAccount
        count, _ = BankAccount.objects.filter(id=stripe_bank_account["id"]).delete()
        self.assertEqual(1, count)

    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    def test_remove_already_deleted_bankaccount_by_account(
        self,
        account_retrieve_mock,
    ):
        stripe_bank_account = BankAccount._api_create(
            account=self.account, source=FAKE_BANK_ACCOUNT_IV["id"]
        )
        BankAccount.sync_from_stripe_data(stripe_bank_account)

        # remove BankAccount
        count, _ = BankAccount.objects.filter(id=stripe_bank_account["id"]).delete()
        self.assertEqual(1, count)

        # remove BankAccount again
        count, _ = BankAccount.objects.filter(id=stripe_bank_account["id"]).delete()
        self.assertEqual(0, count)

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

        self.assertCountEqual(
            [FAKE_BANK_ACCOUNT_SOURCE], [i for i in bank_account_list]
        )
