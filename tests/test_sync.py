"""
dj-stripe Sync Method Tests.
"""

from copy import deepcopy
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.test.testcases import TestCase
from stripe import InvalidRequestError

from djstripe.enums import APIKeyType
from djstripe.models import APIKey, Customer
from djstripe.management.commands.djstripe_sync_models import Command
from djstripe.settings import djstripe_settings
from djstripe.sync import sync_subscriber

from . import FAKE_CUSTOMER, StripeList
from .conftest import CreateAccountMixin


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

        with self.assertLogs("djstripe.sync", level="ERROR") as logs:
            sync_subscriber(self.user)

        self.assertIn("Failed to sync subscriber", logs.output[0])
        self.assertIn("No such customer:", logs.output[0])


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

        # Regression: must not pass `id=` (Customer's pk) when listing sources;
        # Stripe rejects unknown kwargs and the call would fail in production.
        for _, kwargs in list_sources_mock.call_args_list:
            assert "id" not in kwargs
            assert kwargs["customer"] == "cus_test"
        assert {kwargs["object"] for _, kwargs in list_sources_mock.call_args_list} == {
            "card",
            "bank_account",
        }
        assert start_sync_mock.call_count == 2

    SK_TEST = "sk_test_" + "a" * 24

    def test_call_command_does_not_raise_on_sync_failure(self):
        # Programmatic call_command() must not raise even when a sync fails, so
        # callers like the admin "Sync All Instances" action keep working.
        with patch.object(Command, "sync_model", return_value=False):
            stderr = StringIO()
            call_command(
                "djstripe_sync_models",
                "Account",
                api_keys=[self.SK_TEST],
                stderr=stderr,
            )
        assert "sync(s) failed" in stderr.getvalue()

    def test_fail_on_error_raises_on_sync_failure(self):
        # With --fail-on-error (or its programmatic equivalent), a failed sync
        # must surface as a non-zero exit / CommandError for cron and CI.
        with patch.object(Command, "sync_model", return_value=False):
            with self.assertRaises(CommandError):
                call_command(
                    "djstripe_sync_models",
                    "Account",
                    api_keys=[self.SK_TEST],
                    fail_on_error=True,
                )


class TestSyncModelsGetApiKeys(TestCase):
    """Tests for resolving which API keys djstripe_sync_models will sync."""

    SK_TEST = "sk_test_" + "a" * 24
    SK_LIVE = "sk_live_" + "b" * 24
    PK_TEST = "pk_test_" + "c" * 24

    def test_explicit_keys_are_used_without_db_lookup(self):
        # Regression for #2100: explicitly passed keys must work even if they're
        # not stored in the database.
        keys = [self.SK_TEST, self.SK_LIVE]
        assert Command().get_api_keys(keys) == keys

    def test_explicit_invalid_key_raises(self):
        with self.assertRaises(CommandError):
            Command().get_api_keys(["not-a-valid-key"])

    def test_falls_back_to_settings_keys(self):
        # Regression for #2100: with no keys in the database, fall back to the
        # keys defined in the settings (environment variables).
        assert APIKey.objects.count() == 0
        assert Command().get_api_keys(None) == djstripe_settings.get_api_keys()

    def test_merges_db_and_settings_keys_and_skips_publishable(self):
        APIKey.objects.create(
            type=APIKeyType.secret, secret=self.SK_TEST, livemode=False
        )
        APIKey.objects.create(
            type=APIKeyType.publishable, secret=self.PK_TEST, livemode=False
        )

        resolved = Command().get_api_keys(None)

        assert self.SK_TEST in resolved
        # publishable keys can't list resources, so they must be excluded
        assert self.PK_TEST not in resolved
        for secret in djstripe_settings.get_api_keys():
            assert secret in resolved

    @override_settings(
        STRIPE_SECRET_KEY="", STRIPE_TEST_SECRET_KEY="", STRIPE_LIVE_SECRET_KEY=""
    )
    def test_handle_with_no_keys_anywhere_prints_helpful_error(self):
        assert APIKey.objects.count() == 0
        stderr = StringIO()
        call_command("djstripe_sync_models", "Account", stderr=stderr)
        assert "don't have any API Keys" in stderr.getvalue()
