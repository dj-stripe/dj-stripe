"""
dj-stripe APIKey model tests
"""

from copy import deepcopy
from unittest.mock import patch

import pytest
import stripe
from django.test import TestCase

from djstripe.admin.admin import APIKeyAdminCreateForm
from djstripe.enums import APIKeyType
from djstripe.exceptions import InvalidStripeAPIKey
from djstripe.models import Account, APIKey
from djstripe.models.api import get_api_key_details_by_prefix
from djstripe.utils import owner_account_cache

from . import FAKE_FILEUPLOAD_ICON, FAKE_FILEUPLOAD_LOGO, FAKE_PLATFORM_ACCOUNT
from .conftest import CreateAccountMixin

pytestmark = pytest.mark.django_db
# avoid literal api keys to prevent git secret scanners false-positives
SK_TEST = "sk_test_" + "XXXXXXXXXXXXXXXXXXXX1234"
SK_LIVE = "sk_live_" + "XXXXXXXXXXXXXXXXXXXX5678"
RK_TEST = "rk_test_" + "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX9876"
RK_LIVE = "rk_live_" + "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX5432"
PK_TEST = "pk_test_" + "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXAAAA"
PK_LIVE = "pk_live_" + "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXBBBB"


def test_get_api_key_details_by_prefix():
    assert get_api_key_details_by_prefix(SK_TEST) == (APIKeyType.secret, False)
    assert get_api_key_details_by_prefix(SK_LIVE) == (APIKeyType.secret, True)
    assert get_api_key_details_by_prefix(RK_TEST) == (APIKeyType.restricted, False)
    assert get_api_key_details_by_prefix(RK_LIVE) == (APIKeyType.restricted, True)
    assert get_api_key_details_by_prefix(PK_TEST) == (APIKeyType.publishable, False)
    assert get_api_key_details_by_prefix(PK_LIVE) == (APIKeyType.publishable, True)


def test_get_api_key_details_by_prefix_bad_values():
    with pytest.raises(InvalidStripeAPIKey):
        get_api_key_details_by_prefix("pk_a")
    with pytest.raises(InvalidStripeAPIKey):
        get_api_key_details_by_prefix("sk_a")
    with pytest.raises(InvalidStripeAPIKey):
        get_api_key_details_by_prefix("rk_nope_1234")
    # trailing junk after the key body must be rejected (regex is end-anchored)
    with pytest.raises(InvalidStripeAPIKey):
        get_api_key_details_by_prefix(SK_TEST + " not a key")


def test_get_api_key_details_by_prefix_long_key():
    # Modern Stripe keys exceed the old 99-character body limit; they must parse.
    long_key = "sk_test_" + "A" * 107
    assert get_api_key_details_by_prefix(long_key) == (APIKeyType.secret, False)


def test_clean_public_apikey():
    key = APIKey(type=APIKeyType.publishable, livemode=False, secret=PK_TEST)
    assert not key.djstripe_owner_account
    key.clean()
    assert not key.djstripe_owner_account


@patch("stripe.Account.retrieve", return_value=deepcopy(FAKE_PLATFORM_ACCOUNT))
@patch("stripe.File.retrieve", return_value=deepcopy(FAKE_FILEUPLOAD_ICON))
def test_apikey_detect_livemode_and_type(
    fileupload_retrieve_mock, account_retrieve_mock, monkeypatch
):
    def mock_account_retrieve(*args, **kwargs):
        return FAKE_PLATFORM_ACCOUNT

    monkeypatch.setattr(stripe.Account, "retrieve", mock_account_retrieve)

    # create a Stripe Platform Account
    FAKE_PLATFORM_ACCOUNT.create()

    keys_and_values = (
        (PK_TEST, False, APIKeyType.publishable),
        (RK_TEST, False, APIKeyType.restricted),
        (SK_TEST, False, APIKeyType.secret),
        (PK_LIVE, True, APIKeyType.publishable),
        (RK_LIVE, True, APIKeyType.restricted),
        (SK_LIVE, True, APIKeyType.secret),
    )
    for secret, livemode, type in keys_and_values:
        # need to use ModelAdmin Form to create the APIKey instance
        form = APIKeyAdminCreateForm(
            data={"secret": secret},
        )
        form.save()

        key = form.instance

        assert key.livemode is livemode
        assert key.type is type


class APIKeyTest(CreateAccountMixin, TestCase):
    def setUp(self):
        # create a Stripe Platform Account
        self.account = FAKE_PLATFORM_ACCOUNT.create()

        self.apikey_test = APIKey.objects.create(
            type=APIKeyType.secret,
            name="Test Secret Key",
            secret=SK_TEST,
            livemode=False,
            djstripe_owner_account=self.account,
        )

        self.apikey_restricted_test = APIKey.objects.create(
            type=APIKeyType.secret,
            name="Test Restricted Secret Key",
            secret=RK_TEST,
            livemode=False,
            djstripe_owner_account=self.account,
        )

        self.apikey_live = APIKey.objects.create(
            type=APIKeyType.secret,
            name="Live Secret Key",
            secret=SK_LIVE,
            livemode=True,
            djstripe_owner_account=self.account,
        )

    def test_get_stripe_dashboard_url(self):
        self.assertEqual(
            self.apikey_test.get_stripe_dashboard_url(),
            "https://dashboard.stripe.com/acct_1Fg9jUA3kq9o1aTc/test/apikeys",
        )
        self.assertEqual(
            self.apikey_live.get_stripe_dashboard_url(),
            "https://dashboard.stripe.com/acct_1Fg9jUA3kq9o1aTc/apikeys",
        )

    def test___str__(self):
        assert str(self.apikey_live) == "Live Secret Key"
        assert str(self.apikey_test) == "Test Secret Key"

        # update name of apikey_live to ""
        self.apikey_live.name = ""
        self.apikey_live.save()

        assert str(self.apikey_live) == "sk_live_...5678"

    def test_secret_redacted(self):
        self.assertEqual(self.apikey_test.secret_redacted, "sk_test_...1234")
        self.assertEqual(self.apikey_live.secret_redacted, "sk_live_...5678")

    def test_secret_not_in_str(self):
        assert self.apikey_test.secret not in str(self.apikey_test)
        assert self.apikey_live.secret not in str(self.apikey_live)

    def test_get_account_by_api_key(self):
        account = Account.get_or_retrieve_for_api_key(self.apikey_test.secret)
        assert account == self.account

    def test_get_account_by_api_key_hits_the_db_every_time_by_default(self):
        # Each resolution costs a savepoint, an APIKey lookup, the owner
        # account dereference, and the savepoint release.
        with self.assertNumQueries(8):
            for _ in range(2):
                assert (
                    Account.get_or_retrieve_for_api_key(self.apikey_test.secret)
                    == self.account
                )

    def test_owner_account_cache_resolves_each_key_once(self):
        """Inside the cache, repeat lookups of a key don't touch the database."""
        with owner_account_cache(), self.assertNumQueries(4):
            for _ in range(5):
                assert (
                    Account.get_or_retrieve_for_api_key(self.apikey_test.secret)
                    == self.account
                )

    def test_owner_account_cache_is_per_key(self):
        """Each distinct key is still resolved (once) on its own."""
        with owner_account_cache(), self.assertNumQueries(8):
            for secret in (self.apikey_test.secret, self.apikey_live.secret):
                for _ in range(3):
                    assert Account.get_or_retrieve_for_api_key(secret) == self.account

    def test_owner_account_cache_does_not_outlive_the_block(self):
        """Leaving the block discards the cache rather than leaking it."""
        with owner_account_cache():
            Account.get_or_retrieve_for_api_key(self.apikey_test.secret)

        with self.assertNumQueries(4):
            assert (
                Account.get_or_retrieve_for_api_key(self.apikey_test.secret)
                == self.account
            )

    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.File.retrieve",
        side_effect=[deepcopy(FAKE_FILEUPLOAD_ICON), deepcopy(FAKE_FILEUPLOAD_LOGO)],
        autospec=True,
    )
    def test_refresh_account(self, fileupload_retrieve_mock, account_retrieve_mock):
        for key in (
            "apikey_test",
            "apikey_restricted_test",
        ):
            # remove djstripe_owner_account field
            instance = getattr(self, key)
            instance.djstripe_owner_account = None
            instance.save()

            # invoke refresh_Account()
            instance.refresh_account()
            assert instance.djstripe_owner_account.id == FAKE_PLATFORM_ACCOUNT["id"]
