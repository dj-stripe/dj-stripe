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

from djstripe import models
from djstripe.enums import APIKeyType
from djstripe.management.commands.djstripe_sync_models import Command
from djstripe.models import Account, APIKey, BankAccount, Card, Customer
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
    def test_customer_sync_does_not_list_removed_legacy_sources(
        self, list_sources_mock
    ):
        # Legacy customer cards and bank accounts were removed in 2.11. A key
        # that can read customers must not also need to list those sources.
        list_sources_mock.side_effect = StripePermissionError("not permitted")
        customer = Customer(id="cus_test")
        command = Command(stderr=StringIO())

        with (
            patch.object(
                command,
                "get_list_kwargs",
                return_value=[{"api_key": self.SK_TEST, "stripe_account": "acct_test"}],
            ),
            patch.object(
                Customer, "api_list", return_value=StripeList(data=[FAKE_CUSTOMER])
            ),
            patch.object(Customer, "sync_from_stripe_data", return_value=customer),
        ):
            assert command.sync_model(Customer, api_key=self.SK_TEST)

        list_sources_mock.assert_not_called()
        assert command.stderr.getvalue() == ""

    @patch("stripe.Account.list_external_accounts", autospec=True)
    def test_connected_account_sync_still_lists_external_accounts(self, list_mock):
        command = Command()
        for account_type in ("express", "custom"):
            account = Account(id="acct_connected", stripe_data={"type": account_type})
            bank = StripeItem(id="ba_test", object="bank_account")
            card = StripeItem(id="card_test", object="card")
            items = StripeList(data=[bank, card])
            list_mock.return_value = items
            with (
                patch.object(
                    BankAccount,
                    "sync_from_stripe_data",
                    return_value=BankAccount(id=bank.id),
                ) as bank_sync,
                patch.object(
                    Card, "sync_from_stripe_data", return_value=Card(id=card.id)
                ) as card_sync,
            ):
                command.sync_bank_accounts_and_cards(
                    account, stripe_account=account.id, api_key=self.SK_TEST
                )
            list_mock.assert_called_with(
                account.id,
                api_key=self.SK_TEST,
                stripe_account=account.id,
                stripe_version=djstripe_settings.STRIPE_API_VERSION,
            )
            bank_sync.assert_called_once_with(bank, api_key=self.SK_TEST)
            card_sync.assert_called_once_with(card, api_key=self.SK_TEST)

    @patch("stripe.Account.list_external_accounts", autospec=True)
    def test_standard_account_sync_does_not_list_external_accounts(self, list_mock):
        account = Account(id="acct_standard", stripe_data={"type": "standard"})
        Command().sync_bank_accounts_and_cards(
            account, stripe_account=account.id, api_key=self.SK_TEST
        )
        list_mock.assert_not_called()

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

    def test_connected_accounts_are_enumerated_once_per_key(self):
        # Enumerating the connected accounts costs a platform retrieve plus a
        # full paginated list, and the answer is the same for every model in
        # the run. Doing it per (model, key) pair made a sync of a platform
        # with N connected accounts pay for that enumeration ~50 times over.
        stderr = StringIO()

        with (
            patch.object(
                Command, "get_stripe_account", return_value={"acct_test"}
            ) as get_stripe_account_mock,
            patch(
                "djstripe.models.Customer.api_list", return_value=StripeList(data=[])
            ),
            patch("djstripe.models.Coupon.api_list", return_value=StripeList(data=[])),
            patch("djstripe.models.Account.api_list", return_value=StripeList(data=[])),
        ):
            call_command(
                "djstripe_sync_models",
                "Customer",
                "Coupon",
                api_keys=[self.RK_TEST],
                stderr=stderr,
            )

        assert stderr.getvalue() == ""
        get_stripe_account_mock.assert_called_once_with(api_key=self.RK_TEST)

    def test_nested_list_kwargs_are_yielded_lazily(self):
        # Handlers that enumerate a parent resource (an invoice per line item
        # here) used to materialise every id before a single object was synced.
        command = Command()
        command._accounts_by_api_key[self.RK_TEST] = {""}

        invoices = StripeList(data=[StripeItem(id="in_one"), StripeItem(id="in_two")])

        with patch(
            "djstripe.models.Invoice.api_list", return_value=invoices
        ) as invoice_list_mock:
            list_kwargs = command.get_list_kwargs(models.LineItem, api_key=self.RK_TEST)
            invoice_list_mock.assert_not_called()

            first = next(iter(list_kwargs))

        assert first["id"] == "in_one"

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

    def test_the_account_cache_is_keyed_by_api_key(self):
        # A cache shared across keys would hand one key another key's accounts.
        command = Command()
        other_key = "rk_test_" + "f" * 24

        def accounts(api_key):
            return {
                kwargs["stripe_account"]
                for kwargs in command.get_list_kwargs(models.Coupon, api_key=api_key)
            }

        with patch.object(
            Command, "get_stripe_account", side_effect=[{"acct_a"}, {"acct_b"}]
        ) as get_mock:
            first = accounts(self.RK_TEST)
            second = accounts(other_key)
            # ...and repeats still come from the cache.
            assert accounts(self.RK_TEST) == first

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
