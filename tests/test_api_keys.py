from copy import deepcopy
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from djstripe import models
from djstripe.enums import APIKeyType
from djstripe.settings import djstripe_settings

from . import FAKE_ACCOUNT, FAKE_FILEUPLOAD_LOGO


class TestCheckApiKeySettings(TestCase):
    @override_settings(
        STRIPE_LIVE_SECRET_KEY="sk_live_foo",
        STRIPE_LIVE_PUBLIC_KEY="sk_live_foo",
        STRIPE_LIVE_MODE=True,
    )
    @patch("stripe.Account.retrieve", autospec=True)
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_LOGO),
        autospec=True,
    )
    def test_global_api_keys_live_mode(
        self,
        fileupload_retrieve_mock,
        account_retrieve_mock,
    ):
        fake_account = deepcopy(FAKE_ACCOUNT)
        fake_account["settings"]["branding"]["icon"] = None
        account_retrieve_mock.return_value = fake_account

        with patch.object(
            models.api,
            "get_api_key_details_by_prefix",
            return_value=(APIKeyType.secret, True),
        ):
            account = models.Account.sync_from_stripe_data(
                fake_account, api_key=djstripe_settings.STRIPE_SECRET_KEY
            )
            self.assertEqual(account.default_api_key, "sk_live_foo")

        self.assertEqual(djstripe_settings.STRIPE_LIVE_MODE, True)
        self.assertEqual(djstripe_settings.STRIPE_SECRET_KEY, "sk_live_foo")
        self.assertEqual(djstripe_settings.LIVE_API_KEY, "sk_live_foo")

    @override_settings(
        STRIPE_TEST_SECRET_KEY="sk_test_foo",
        STRIPE_TEST_PUBLIC_KEY="pk_test_foo",
        STRIPE_LIVE_MODE=False,
    )
    @patch("stripe.Account.retrieve", autospec=True)
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_LOGO),
        autospec=True,
    )
    def test_global_api_keys_test_mode(
        self,
        fileupload_retrieve_mock,
        account_retrieve_mock,
    ):
        fake_account = deepcopy(FAKE_ACCOUNT)
        fake_account["settings"]["branding"]["icon"] = None
        account_retrieve_mock.return_value = fake_account

        with patch.object(
            models.api,
            "get_api_key_details_by_prefix",
            return_value=(APIKeyType.secret, False),
        ):
            account = models.Account.sync_from_stripe_data(
                fake_account, api_key=djstripe_settings.STRIPE_SECRET_KEY
            )
            self.assertEqual(account.default_api_key, "sk_test_foo")

        self.assertEqual(djstripe_settings.STRIPE_LIVE_MODE, False)
        self.assertEqual(djstripe_settings.STRIPE_SECRET_KEY, "sk_test_foo")
        self.assertEqual(djstripe_settings.TEST_API_KEY, "sk_test_foo")

    @override_settings(
        STRIPE_TEST_SECRET_KEY="sk_test_foo",
        STRIPE_LIVE_SECRET_KEY="sk_live_foo",
        STRIPE_TEST_PUBLIC_KEY="pk_test_foo",
        STRIPE_LIVE_PUBLIC_KEY="pk_live_foo",
        STRIPE_LIVE_MODE=True,
    )
    @patch("stripe.Account.retrieve", autospec=True)
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_LOGO),
        autospec=True,
    )
    def test_api_key_live_mode(
        self,
        fileupload_retrieve_mock,
        account_retrieve_mock,
    ):
        fake_account = deepcopy(FAKE_ACCOUNT)
        fake_account["settings"]["branding"]["icon"] = None
        account_retrieve_mock.return_value = fake_account

        with patch.object(
            models.api,
            "get_api_key_details_by_prefix",
            return_value=(APIKeyType.secret, True),
        ):
            account = models.Account.sync_from_stripe_data(
                fake_account, api_key=djstripe_settings.STRIPE_SECRET_KEY
            )
            self.assertEqual(account.default_api_key, "sk_live_foo")

        del settings.STRIPE_SECRET_KEY, settings.STRIPE_TEST_SECRET_KEY
        del settings.STRIPE_PUBLIC_KEY, settings.STRIPE_TEST_PUBLIC_KEY
        self.assertEqual(djstripe_settings.STRIPE_LIVE_MODE, True)
        self.assertEqual(djstripe_settings.STRIPE_SECRET_KEY, "sk_live_foo")
        self.assertEqual(djstripe_settings.STRIPE_PUBLIC_KEY, "pk_live_foo")

    @override_settings(
        STRIPE_TEST_SECRET_KEY="sk_test_foo",
        STRIPE_LIVE_SECRET_KEY="sk_live_foo",
        STRIPE_TEST_PUBLIC_KEY="pk_test_foo",
        STRIPE_LIVE_PUBLIC_KEY="pk_live_foo",
        STRIPE_LIVE_MODE=False,
    )
    @patch("stripe.Account.retrieve", autospec=True)
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_LOGO),
        autospec=True,
    )
    def test_secret_key_test_mode(
        self,
        fileupload_retrieve_mock,
        account_retrieve_mock,
    ):
        fake_account = deepcopy(FAKE_ACCOUNT)
        fake_account["settings"]["branding"]["icon"] = None
        account_retrieve_mock.return_value = fake_account

        with patch.object(
            models.api,
            "get_api_key_details_by_prefix",
            return_value=(APIKeyType.secret, False),
        ):
            account = models.Account.sync_from_stripe_data(
                fake_account, api_key=djstripe_settings.STRIPE_SECRET_KEY
            )
            self.assertEqual(account.default_api_key, "sk_test_foo")

        del settings.STRIPE_SECRET_KEY
        del settings.STRIPE_PUBLIC_KEY
        self.assertEqual(djstripe_settings.STRIPE_LIVE_MODE, False)
        self.assertEqual(djstripe_settings.STRIPE_SECRET_KEY, "sk_test_foo")
        self.assertEqual(djstripe_settings.STRIPE_PUBLIC_KEY, "pk_test_foo")
        self.assertEqual(djstripe_settings.TEST_API_KEY, "sk_test_foo")
