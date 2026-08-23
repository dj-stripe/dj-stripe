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
from stripe import PermissionError as StripePermissionError

from djstripe.enums import APIKeyType
from djstripe.management.commands.djstripe_sync_models import Command
from djstripe.models import Account, APIKey, Customer
from djstripe.settings import djstripe_settings
from djstripe.sync import sync_subscriber

from . import FAKE_CUSTOMER, StripeItem, StripeList
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


class TestSyncModelsRestrictedKeys(TestCase):
    """
    Restricted keys are handled by asking Stripe, not by sniffing the prefix.

    Regression tests for #1908: syncing with `--api-keys rk_...` crashed with
    `'NoneType' object has no attribute 'id'`, because the restricted-key guard
    in `Account.get_default_account()` inspected the key configured in settings
    rather than the key it was passed.
    """

    RK_TEST = "rk_test_" + "d" * 24

    def test_get_default_account_is_none_when_the_account_is_not_permitted(self):
        with patch(
            "stripe.Account.retrieve",
            side_effect=StripePermissionError("not permitted"),
        ) as retrieve_mock:
            assert Account.get_default_account(api_key=self.RK_TEST) is None

        # The call is attempted: Stripe decides, the key prefix does not.
        retrieve_mock.assert_called_once()

    def test_get_stripe_account_falls_back_when_the_platform_account_is_denied(self):
        # Losing the platform account id must not cost us the connected ones,
        # and the key's own account must still be represented -- by the empty
        # string, which omits the Stripe-Account header on the resulting calls.
        connected = StripeList(
            data=[StripeItem(id="acct_one"), StripeItem(id="acct_two")]
        )

        with (
            patch(
                "stripe.Account.retrieve",
                side_effect=StripePermissionError("not permitted"),
            ),
            patch("djstripe.models.Account.api_list", return_value=connected),
        ):
            accounts = Command.get_stripe_account(api_key=self.RK_TEST)

        assert accounts == {"", "acct_one", "acct_two"}

    def test_get_stripe_account_survives_unlistable_connected_accounts(self):
        # A restricted key scoped to, say, customer-read only cannot list
        # connected accounts. That must not abort the sync of its own account.
        with (
            patch(
                "stripe.Account.retrieve",
                side_effect=StripePermissionError("not permitted"),
            ),
            patch(
                "djstripe.models.Account.api_list",
                side_effect=StripePermissionError("not permitted"),
            ),
        ):
            accounts = Command.get_stripe_account(api_key=self.RK_TEST)

        assert accounts == {""}

    def test_sync_with_restricted_key_actually_syncs(self):
        # Regression: losing the platform retrieve must not leave the account
        # set empty, which would build no list kwargs and silently sync nothing
        # while still exiting successfully.
        stderr = StringIO()

        with (
            patch(
                "stripe.Account.retrieve",
                side_effect=StripePermissionError("not permitted"),
            ),
            patch(
                "djstripe.models.Customer.api_list", return_value=StripeList(data=[])
            ) as api_list_mock,
            patch("djstripe.models.Account.api_list", return_value=StripeList(data=[])),
        ):
            call_command(
                "djstripe_sync_models",
                "Customer",
                api_keys=[self.RK_TEST],
                stderr=stderr,
            )

        assert api_list_mock.called, "restricted-key sync did no work at all"
        assert api_list_mock.call_args.kwargs["stripe_account"] == ""
        assert stderr.getvalue() == ""

    def test_the_account_set_is_resolved_once_per_key(self):
        # get_list_kwargs asks per model, so without memoisation a full sync
        # pays one rejected round-trip per model rather than one per key.
        command = Command()
        sentinel = {""}

        with patch.object(
            Command, "get_stripe_account", return_value=sentinel
        ) as get_mock:
            for _ in range(5):
                assert command.get_stripe_account_cached(self.RK_TEST) is sentinel

        get_mock.assert_called_once()

    def test_the_account_cache_is_keyed_by_api_key(self):
        # A cache shared across keys would hand one key another key's accounts.
        command = Command()
        other_key = "rk_test_" + "f" * 24

        with patch.object(
            Command, "get_stripe_account", side_effect=[{"acct_a"}, {"acct_b"}]
        ) as get_mock:
            first = command.get_stripe_account_cached(self.RK_TEST)
            second = command.get_stripe_account_cached(other_key)
            # ...and repeats still come from the cache.
            assert command.get_stripe_account_cached(self.RK_TEST) == first

        assert first == {"acct_a"}
        assert second == {"acct_b"}
        assert get_mock.call_count == 2

    @override_settings(
        STRIPE_TEST_SECRET_KEY="rk_test_" + "e" * 24, STRIPE_LIVE_SECRET_KEY=""
    )
    def test_sync_account_does_not_dereference_missing_default_account(self):
        # The originally reported failure: with a restricted key configured,
        # `get_default_account()` returns None and the command then blew up
        # dereferencing `.id` on it. `get_stripe_account` is stubbed so the run
        # reaches that line instead of failing earlier on the platform retrieve.
        stderr = StringIO()

        with (
            patch.object(Command, "get_stripe_account", return_value={"acct_test"}),
            patch(
                "stripe.Account.retrieve",
                side_effect=StripePermissionError("not permitted"),
            ),
            patch("djstripe.models.Account.api_list", return_value=StripeList(data=[])),
        ):
            call_command("djstripe_sync_models", "Account", stderr=stderr)

        # Assert on the outcome, not just on the absence of the old error
        # string: nothing should be reported as failed at all.
        assert stderr.getvalue() == ""
