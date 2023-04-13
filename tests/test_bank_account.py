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
from djstripe.models import BankAccount, Customer
from djstripe.models.base import IdempotencyKey
from djstripe.settings import djstripe_settings

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
        "fake_stripe_data, has_account, has_customer",
        [
            (deepcopy(FAKE_BANK_ACCOUNT_IV), True, False),
            (deepcopy(FAKE_BANK_ACCOUNT_SOURCE), False, True),
            (deepcopy(FAKE_BANK_ACCOUNT_IV), False, False),
        ],
    )
    def test__str__(self, fake_stripe_data, has_account, has_customer, monkeypatch):
        def mock_customer_get(*args, **kwargs):
            data = deepcopy(FAKE_CUSTOMER_IV)
            data["default_source"] = None
            data["sources"] = []
            return data

        def mock_account_get(*args, **kwargs):
            return deepcopy(FAKE_CUSTOM_ACCOUNT)

        # monkeypatch stripe.Account.retrieve and stripe.Customer.retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Account, "retrieve", mock_account_get)
        monkeypatch.setattr(stripe.Customer, "retrieve", mock_customer_get)

        bankaccount = BankAccount.sync_from_stripe_data(fake_stripe_data)
        default = False

        if has_account:
            default = fake_stripe_data["default_for_currency"]
            assert (
                f"{fake_stripe_data['bank_name']} {fake_stripe_data['currency']} {'Default' if default else ''} {fake_stripe_data['routing_number']} {fake_stripe_data['last4']}"
                == str(bankaccount)
            )
        if has_customer:
            customer = Customer.objects.filter(id=fake_stripe_data["customer"]).first()

            default_source = customer.default_source
            default_payment_method = customer.default_payment_method

            if (
                default_payment_method
                and fake_stripe_data["id"] == default_payment_method.id
            ) or (default_source and fake_stripe_data["id"] == default_source.id):
                # current bankaccount is the default payment method or source
                default = True

            assert (
                f"{fake_stripe_data['bank_name']} {fake_stripe_data['routing_number']} ({bankaccount.human_readable_status}) {'Default' if default else ''} {fake_stripe_data['currency']}"
                == str(bankaccount)
            )
        if not has_account and not has_customer:
            # ensure account and customer do not exist
            fake_stripe_data_2 = deepcopy(fake_stripe_data)
            fake_stripe_data_2["account"] = None
            fake_stripe_data_2["customer"] = None

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
        def mock_customer_get(*args, **kwargs):
            data = deepcopy(FAKE_CUSTOMER_IV)
            data["default_source"] = None
            data["sources"] = []
            return data

        def mock_account_get(*args, **kwargs):
            return deepcopy(FAKE_CUSTOM_ACCOUNT)

        # monkeypatch stripe.Account.retrieve and stripe.Customer.retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Account, "retrieve", mock_account_get)
        monkeypatch.setattr(stripe.Customer, "retrieve", mock_customer_get)

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
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_BANK_ACCOUNT_IV),
        autospec=True,
    )
    def test_api_retrieve_by_customer_equals_retrieval_by_account(
        self, account_retrieve_external_account_mock, customer_retrieve_mock
    ):
        # deepcopy the BankAccount object
        FAKE_BANK_ACCOUNT_DICT = deepcopy(FAKE_BANK_ACCOUNT_IV)

        bankaccount = BankAccount.sync_from_stripe_data(FAKE_BANK_ACCOUNT_DICT)
        bankaccount_by_customer = bankaccount.api_retrieve()

        # Add account
        FAKE_BANK_ACCOUNT_DICT["account"] = FAKE_CUSTOM_ACCOUNT["id"]
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
        FAKE_BANK_ACCOUNT_DICT["account"] = self.standard_account.id

        bank_account = BankAccount.sync_from_stripe_data(FAKE_BANK_ACCOUNT_DICT)

        self.assertEqual(self.customer, bank_account.customer)
        self.assertEqual(self.standard_account, bank_account.account)
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
                "djstripe.BankAccount.customer",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.default_source",
                "djstripe.Customer.coupon",
            },
        )

    def test_api_call_no_customer_and_no_account(self):
        exception_message = (
            "BankAccount objects must be manipulated through either a Stripe Connected Account or a customer. "
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
            "BankAccount objects must be manipulated through a Customer. "
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
            "BankAccount objects must be manipulated through a Stripe Connected Account. "
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
        "tests.Sources",
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_IV),
        autospec=True,
    )
    def test__api_create_with_account_absent(
        self, customer_retrieve_mock, sources_mock
    ):
        # Need to patch tests.Sources.create method
        sources_create_mock = sources_mock.return_value.create
        sources_create_mock.return_value = FAKE_CUSTOMER_IV["sources"]["data"][0]

        stripe_bank_account = BankAccount._api_create(
            customer=self.customer, source=FAKE_BANK_ACCOUNT_SOURCE["id"]
        )

        # Get just created IdempotencyKey
        idempotency_key = IdempotencyKey.objects.get(
            action=f"bankaccount:create:{FAKE_BANK_ACCOUNT_SOURCE['id']}",
            livemode=False,
        )
        idempotency_key = str(idempotency_key.uuid)

        self.assertEqual(FAKE_BANK_ACCOUNT_SOURCE, stripe_bank_account)

        sources_create_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
            idempotency_key=idempotency_key,
            source=FAKE_BANK_ACCOUNT_SOURCE["id"],
            metadata={"idempotency_key": idempotency_key},
        )

    @patch(
        "tests.Sources",
        autospec=True,
    )
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
        self, account_retrieve_mock, customer_retrieve_mock, sources_mock
    ):
        FAKE_BANK_ACCOUNT_DICT = deepcopy(FAKE_BANK_ACCOUNT_SOURCE)
        FAKE_BANK_ACCOUNT_DICT["account"] = FAKE_CUSTOM_ACCOUNT["id"]

        # Need to patch tests.Sources.create method
        sources_create_mock = sources_mock.return_value.create
        sources_create_mock.return_value = FAKE_CUSTOMER_IV["sources"]["data"][0]

        stripe_bank_account = BankAccount._api_create(
            account=self.custom_account,
            customer=self.customer,
            source=FAKE_BANK_ACCOUNT_DICT["id"],
        )

        # Get just created IdempotencyKey
        idempotency_key = IdempotencyKey.objects.get(
            action=f"bankaccount:create:{FAKE_BANK_ACCOUNT_SOURCE['id']}",
            livemode=False,
        )
        idempotency_key = str(idempotency_key.uuid)

        self.assertEqual(FAKE_BANK_ACCOUNT_SOURCE, stripe_bank_account)

        sources_create_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
            idempotency_key=idempotency_key,
            source=FAKE_BANK_ACCOUNT_SOURCE["id"],
            metadata={"idempotency_key": idempotency_key},
        )

    @patch(
        "tests.ExternalAccounts",
        autospec=True,
    )
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
        self, account_retrieve_mock, customer_retrieve_mock, external_accounts_mock
    ):
        # Need to patch tests.Sources.create method
        external_accounts_create_mock = external_accounts_mock.return_value.create
        external_accounts_create_mock.return_value = FAKE_BANK_ACCOUNT_IV

        stripe_bank_account = BankAccount._api_create(
            account=self.custom_account, source=FAKE_BANK_ACCOUNT_IV["id"]
        )

        # Get just created IdempotencyKey
        idempotency_key = IdempotencyKey.objects.get(
            action=f"bankaccount:create:{FAKE_BANK_ACCOUNT_IV['id']}",
            livemode=False,
        )
        idempotency_key = str(idempotency_key.uuid)

        self.assertEqual(FAKE_BANK_ACCOUNT_IV, stripe_bank_account)

        external_accounts_create_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
            idempotency_key=idempotency_key,
            source=FAKE_BANK_ACCOUNT_IV["id"],
            metadata={"idempotency_key": idempotency_key},
        )

    @patch(
        "stripe.Customer.delete_source",
        autospec=True,
    )
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
    @patch(
        "stripe.Customer.retrieve_source",
        return_value=deepcopy(FAKE_BANK_ACCOUNT_SOURCE),
        autospec=True,
    )
    def test_remove_bankaccount_by_customer(
        self,
        customer_retrieve_source_mock,
        customer_retrieve_mock,
        bank_account_retrieve_mock,
        bank_account_delete_mock,
    ):
        stripe_bank_account = BankAccount._api_create(
            customer=self.customer, source=FAKE_BANK_ACCOUNT_SOURCE["id"]
        )
        BankAccount.sync_from_stripe_data(stripe_bank_account)

        self.assertEqual(
            1, BankAccount.objects.filter(id=stripe_bank_account["id"]).count()
        )

        bank_account = self.customer.bank_account.all()[0]
        bank_account.remove()

        self.assertEqual(
            0, BankAccount.objects.filter(id=stripe_bank_account["id"]).count()
        )

        api_key = bank_account.default_api_key
        stripe_account = bank_account._get_stripe_account_id(api_key)

        bank_account_delete_mock.assert_called_once_with(
            self.customer.id,
            bank_account.id,
            api_key=api_key,
            stripe_account=stripe_account,
        )

    @patch(
        "stripe.Account.delete_external_account",
        autospec=True,
    )
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    def test_remove_bankaccount_by_account(
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

        assert bank_account.customer is None
        assert bank_account.account is not None

        # remove BankAccount
        bank_account.remove()

        bank_account_delete_mock.assert_called_once_with(
            self.custom_account.id,
            bank_account.id,
            api_key=api_key,
            stripe_account=stripe_account,
        )

        self.assertEqual(
            0, BankAccount.objects.filter(id=stripe_bank_account["id"]).count()
        )

    @patch(
        "stripe.Account.delete_external_account",
        autospec=True,
    )
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    def test_remove_already_deleted_bankaccount_by_account(
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

        assert bank_account.customer is None
        assert bank_account.account is not None

        # remove BankAccount
        bank_account.remove()
        self.assertEqual(
            0, BankAccount.objects.filter(id=stripe_bank_account["id"]).count()
        )
        bank_account_delete_mock.assert_called_once_with(
            self.custom_account.id,
            bank_account.id,
            api_key=api_key,
            stripe_account=stripe_account,
        )

        # remove BankAccount again
        count, _ = BankAccount.objects.filter(id=stripe_bank_account["id"]).delete()
        self.assertEqual(0, count)

    @patch(
        "stripe.Customer.delete_source",
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_IV),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve_source",
        return_value=deepcopy(FAKE_BANK_ACCOUNT_SOURCE),
        autospec=True,
    )
    def test_remove_already_deleted_bank_account(
        self,
        customer_retrieve_source_mock,
        customer_retrieve_mock,
        bank_account_delete_mock,
    ):
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
