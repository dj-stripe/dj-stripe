"""
dj-stripe Sync Method Tests.
"""

import contextlib
from copy import deepcopy
from unittest.mock import call, patch

from django.contrib.auth import get_user_model
from django.test.testcases import TestCase
from stripe import InvalidRequestError

from djstripe.models import Customer
from djstripe.management.commands.djstripe_sync_models import Command
from djstripe.settings import djstripe_settings
from djstripe.sync import sync_subscriber

from . import FAKE_CUSTOMER, StripeList
from .conftest import CreateAccountMixin


@contextlib.contextmanager
def capture_stdout():
    import sys
    from io import StringIO

    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        yield sys.stdout
    finally:
        sys.stdout = old_stdout


class TestSyncSubscriber(CreateAccountMixin, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="123"
        )

    @patch("djstripe.models.Customer._sync_charges", autospec=True)
    @patch("djstripe.models.Customer._sync_invoices", autospec=True)
    @patch("djstripe.models.Customer._sync_subscriptions", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_success(
        self,
        stripe_customer_create_mock,
        api_retrieve_mock,
        _sync_subscriptions_mock,
        _sync_invoices_mock,
        _sync_charges_mock,
    ):
        sync_subscriber(self.user)
        self.assertEqual(1, Customer.objects.count())
        self.assertEqual(
            FAKE_CUSTOMER["id"],
            Customer.objects.get(subscriber=self.user).api_retrieve()["id"],
        )

        _sync_subscriptions_mock.assert_called_once_with(Customer.objects.first())
        _sync_invoices_mock.assert_called_once_with(Customer.objects.first())
        _sync_charges_mock.assert_called_once_with(Customer.objects.first())

    @patch(
        "djstripe.models.Customer.api_retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_fail(self, stripe_customer_create_mock, api_retrieve_mock):
        api_retrieve_mock.side_effect = InvalidRequestError("No such customer:", "blah")

        with capture_stdout() as stdout:
            sync_subscriber(self.user)

        self.assertEqual("ERROR: No such customer:", stdout.getvalue().strip())


class TestSyncModelsCommand(CreateAccountMixin, TestCase):
    @patch("stripe.Customer.list_sources", autospec=True)
    def test_sync_bank_accounts_and_cards_customer_does_not_pass_id(
        self, list_sources_mock
    ):
        command = Command()
        customer = Customer(id="cus_test")
        list_sources_mock.return_value = StripeList(data=[])

        with patch.object(command, "start_sync") as start_sync_mock:
            command.sync_bank_accounts_and_cards(
                customer, stripe_account="acct_test", api_key="sk_test_123"
            )

        list_sources_mock.assert_has_calls(
            [
                call(
                    customer="cus_test",
                    object="card",
                    api_key="sk_test_123",
                    stripe_account="acct_test",
                    stripe_version=djstripe_settings.STRIPE_API_VERSION,
                ),
                call(
                    customer="cus_test",
                    object="bank_account",
                    api_key="sk_test_123",
                    stripe_account="acct_test",
                    stripe_version=djstripe_settings.STRIPE_API_VERSION,
                ),
            ]
        )

        for _, kwargs in list_sources_mock.call_args_list:
            assert "id" not in kwargs

        assert start_sync_mock.call_count == 2
