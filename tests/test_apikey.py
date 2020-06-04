"""
dj-stripe APIKey model tests
"""

from django.test import TestCase

from djstripe.enums import APIKeyType
from djstripe.models import APIKey

from . import default_account


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
