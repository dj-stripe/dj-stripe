"""
dj-stripe APIKey model tests
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.test import TestCase

from djstripe.enums import APIKeyType
from djstripe.models import Account, APIKey
from djstripe.models.api import get_api_key_details_by_prefix

from . import FAKE_ACCOUNT, FAKE_FILEUPLOAD_ICON, default_account

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
    with pytest.raises(ValueError):
        get_api_key_details_by_prefix("pk_a")
    with pytest.raises(ValueError):
        get_api_key_details_by_prefix("sk_a")
    with pytest.raises(ValueError):
        get_api_key_details_by_prefix("rk_nope_1234")


def test_clean_public_apikey():
    key = APIKey(type=APIKeyType.publishable, livemode=False, secret=PK_TEST)
    assert not key.djstripe_owner_account
    key.clean()
    assert not key.djstripe_owner_account


class APIKeyTest(TestCase):
    def setUp(self):
        self.account = default_account()
        self.apikey_test = APIKey.objects.create(
            type=APIKeyType.secret,
            name="Test Secret Key",
            secret=SK_TEST,
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
            "https://dashboard.stripe.com/acct_TESTXXXXX/test/apikeys",
        )
        self.assertEqual(
            self.apikey_live.get_stripe_dashboard_url(),
            "https://dashboard.stripe.com/acct_TESTXXXXX/apikeys",
        )

    def test_secret_redacted(self):
        self.assertEqual(self.apikey_test.secret_redacted, "sk_test_...1234")
        self.assertEqual(self.apikey_live.secret_redacted, "sk_live_...5678")

    def test_secret_not_in_str(self):
        assert self.apikey_test.secret not in str(self.apikey_test)
        assert self.apikey_live.secret not in str(self.apikey_live)

    def test_get_account_by_api_key(self):
        account = Account.get_or_retrieve_for_api_key(self.apikey_test.secret)
        assert account == self.account

    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_ACCOUNT),
    )
    @patch("stripe.FileUpload.retrieve", return_value=deepcopy(FAKE_FILEUPLOAD_ICON))
    def test_refresh_account(self, fileupload_retrieve_mock, account_retrieve_mock):
        self.apikey_test.djstripe_owner_account = None
        self.apikey_test.save()
        self.apikey_test.clean()
        assert self.apikey_test.djstripe_owner_account.id == FAKE_ACCOUNT["id"]
