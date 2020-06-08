"""
dj-stripe APIKey model tests
"""
import pytest
from django.test import TestCase

from djstripe.enums import APIKeyType
from djstripe.models import Account, APIKey
from djstripe.models.api import get_api_key_details_by_prefix

from . import default_account


def test_get_api_key_details_by_prefix():
    # avoid literal api keys to prevent git secret scanners false-positives
    assert get_api_key_details_by_prefix("sk_test_" + "XXXXXXXXXXXXXXXXXXXX1234") == (
        APIKeyType.secret,
        False,
    )

    assert get_api_key_details_by_prefix("sk_live_" + "XXXXXXXXXXXXXXXXXXXX1234") == (
        APIKeyType.secret,
        True,
    )
    assert get_api_key_details_by_prefix(
        "rk_test_" + "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX9876"
    ) == (APIKeyType.restricted, False)
    assert get_api_key_details_by_prefix(
        "rk_live_" + "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX9876"
    ) == (APIKeyType.restricted, True)
    assert get_api_key_details_by_prefix(
        "pk_test_" + "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXAAAA"
    ) == (APIKeyType.publishable, False)
    assert get_api_key_details_by_prefix(
        "pk_live_" + "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXBBBB"
    ) == (APIKeyType.publishable, True)


def test_get_api_key_details_by_prefix_bad_values():
    with pytest.raises(ValueError):
        get_api_key_details_by_prefix("pk_a")
    with pytest.raises(ValueError):
        get_api_key_details_by_prefix("sk_a")
    with pytest.raises(ValueError):
        get_api_key_details_by_prefix("rk_nope_1234")


class APIKeyTest(TestCase):
    def setUp(self):
        self.account = default_account()
        self.apikey_test = APIKey.objects.create(
            type=APIKeyType.secret,
            name="Test Secret Key",
            secret="sk_test_" + "0123456789XXXXXXXXXX1234",
            livemode=False,
            djstripe_owner_account=self.account,
        )
        self.apikey_live = APIKey.objects.create(
            type=APIKeyType.secret,
            name="Live Secret Key",
            secret="sk_live_" + "0123456789XXXXXXXXXX9876",
            livemode=True,
            djstripe_owner_account=self.account,
        )

    def test_get_stripe_dashboard_url(self):
        self.assertEqual(
            self.apikey_test.get_stripe_dashboard_url(),
            "https://dashboard.stripe.com/test/apikeys",
        )
        self.assertEqual(
            self.apikey_live.get_stripe_dashboard_url(),
            "https://dashboard.stripe.com/apikeys",
        )

    def test_secret_redacted(self):
        self.assertEqual(self.apikey_test.secret_redacted, "sk_test_...1234")
        self.assertEqual(self.apikey_live.secret_redacted, "sk_live_...9876")

    def test_secret_not_in_str(self):
        assert self.apikey_test.secret not in str(self.apikey_test)
        assert self.apikey_live.secret not in str(self.apikey_live)

    def test_get_account_by_api_key(self):
        account = Account.get_or_retrieve_for_api_key(self.apikey_test.secret)
        assert account == self.account
