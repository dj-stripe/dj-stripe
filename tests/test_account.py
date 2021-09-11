"""
dj-stripe Account Tests.
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.test.testcases import TestCase
from django.test.utils import override_settings

from djstripe.models import Account
from djstripe.settings import djstripe_settings

from . import (
    FAKE_ACCOUNT,
    FAKE_FILEUPLOAD_ICON,
    FAKE_FILEUPLOAD_LOGO,
    IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


class TestAccount(AssertStripeFksMixin, TestCase):
    @patch("stripe.Account.retrieve", autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED)
    @patch(
        "stripe.File.retrieve",
        side_effect=[deepcopy(FAKE_FILEUPLOAD_ICON), deepcopy(FAKE_FILEUPLOAD_LOGO)],
        autospec=True,
    )
    def test_get_default_account(self, file_retrieve_mock, account_retrieve_mock):
        account_retrieve_mock.return_value = deepcopy(FAKE_ACCOUNT)

        account = Account.get_default_account()

        account_retrieve_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY
        )

        self.assertGreater(len(account.business_profile), 0)
        self.assertGreater(len(account.settings), 0)

        self.assertEqual(account.branding_icon.id, FAKE_FILEUPLOAD_ICON["id"])
        self.assertEqual(account.branding_logo.id, FAKE_FILEUPLOAD_LOGO["id"])

        self.assertEqual(account.settings["branding"]["icon"], account.branding_icon.id)
        self.assertEqual(account.settings["branding"]["logo"], account.branding_logo.id)

        self.assertNotEqual(account.branding_logo.id, account.branding_icon.id)

        self.assert_fks(account, expected_blank_fks={})

        self.assertEqual(account.business_url, "https://djstripe.com")
        account.business_profile = None
        self.assertEqual(account.business_url, "")

    @patch(
        "stripe.Account.retrieve",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
        return_value=deepcopy(FAKE_ACCOUNT),
    )
    @patch(
        "stripe.File.retrieve",
        side_effect=[deepcopy(FAKE_FILEUPLOAD_ICON), deepcopy(FAKE_FILEUPLOAD_LOGO)],
        autospec=True,
    )
    def test_sync_from_stripe_data(
        self, fileupload_retrieve_mock, account_retrieve_mock
    ):
        fake_account = deepcopy(FAKE_ACCOUNT)
        account = Account.sync_from_stripe_data(fake_account)

        self.assertGreater(len(account.business_profile), 0)
        self.assertGreater(len(account.settings), 0)

        self.assertEqual(account.branding_icon.id, FAKE_FILEUPLOAD_ICON["id"])
        self.assertEqual(account.branding_logo.id, FAKE_FILEUPLOAD_LOGO["id"])

        self.assertEqual(account.settings["branding"]["icon"], account.branding_icon.id)
        self.assertEqual(account.settings["branding"]["logo"], account.branding_logo.id)

        self.assertNotEqual(account.branding_logo.id, account.branding_icon.id)

        self.assert_fks(account, expected_blank_fks={})

        self.assertEqual(account.business_url, "https://djstripe.com")

    @patch(
        "stripe.Account.retrieve",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
        return_value=deepcopy(FAKE_ACCOUNT),
    )
    @patch(
        "stripe.File.retrieve",
        side_effect=[deepcopy(FAKE_FILEUPLOAD_ICON), deepcopy(FAKE_FILEUPLOAD_LOGO)],
        autospec=True,
    )
    def test__find_owner_account(self, fileupload_retrieve_mock, account_retrieve_mock):
        fake_account = deepcopy(FAKE_ACCOUNT)
        account = Account.sync_from_stripe_data(fake_account)
        self.assertEqual(None, Account._find_owner_account(account))

    @patch(
        "stripe.Account.retrieve",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
        return_value=deepcopy(FAKE_ACCOUNT),
    )
    @patch(
        "stripe.File.retrieve",
        side_effect=[deepcopy(FAKE_FILEUPLOAD_ICON), deepcopy(FAKE_FILEUPLOAD_LOGO)],
        autospec=True,
    )
    def test_business_url(self, fileupload_retrieve_mock, account_retrieve_mock):
        fake_account = deepcopy(FAKE_ACCOUNT)
        account = Account.sync_from_stripe_data(fake_account)
        self.assertEqual(fake_account["business_profile"]["url"], account.business_url)

    @patch(
        "stripe.Account.retrieve",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
        return_value=deepcopy(FAKE_ACCOUNT),
    )
    @patch(
        "stripe.File.retrieve",
        side_effect=[deepcopy(FAKE_FILEUPLOAD_ICON), deepcopy(FAKE_FILEUPLOAD_LOGO)],
        autospec=True,
    )
    def test_branding_logo(self, fileupload_retrieve_mock, account_retrieve_mock):
        fake_account = deepcopy(FAKE_ACCOUNT)
        account = Account.sync_from_stripe_data(fake_account)
        self.assertEqual(
            fake_account["settings"]["branding"]["logo"], account.branding_logo.id
        )

    @patch(
        "stripe.Account.retrieve",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
        return_value=deepcopy(FAKE_ACCOUNT),
    )
    @patch(
        "stripe.File.retrieve",
        side_effect=[deepcopy(FAKE_FILEUPLOAD_ICON), deepcopy(FAKE_FILEUPLOAD_LOGO)],
        autospec=True,
    )
    def test_branding_icon(self, fileupload_retrieve_mock, account_retrieve_mock):
        fake_account = deepcopy(FAKE_ACCOUNT)
        account = Account.sync_from_stripe_data(fake_account)
        self.assertEqual(
            fake_account["settings"]["branding"]["icon"], account.branding_icon.id
        )

    @patch("stripe.Account.retrieve", autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED)
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_LOGO),
        autospec=True,
    )
    def test__attach_objects_post_save_hook(
        self, fileupload_retrieve_mock, account_retrieve_mock
    ):
        fake_account = deepcopy(FAKE_ACCOUNT)
        fake_account["settings"]["branding"]["icon"] = None
        account_retrieve_mock.return_value = fake_account

        Account.sync_from_stripe_data(fake_account)

        fileupload_retrieve_mock.assert_called_with(
            id=fake_account["settings"]["branding"]["logo"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            expand=[],
            stripe_account=fake_account["id"],
        )

    @patch("stripe.Account.retrieve", autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED)
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_LOGO),
        autospec=True,
    )
    def test_get_default_account_null_logo(
        self, fileupload_retrieve_mock, account_retrieve_mock
    ):
        fake_account = deepcopy(FAKE_ACCOUNT)
        fake_account["settings"]["branding"]["icon"] = None
        fake_account["settings"]["branding"]["logo"] = None
        account_retrieve_mock.return_value = fake_account

        account = Account.get_default_account()

        account_retrieve_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY
        )

        self.assert_fks(
            account,
            expected_blank_fks={
                "djstripe.Account.branding_logo",
                "djstripe.Account.branding_icon",
            },
        )


class TestAccountStr:
    @pytest.mark.parametrize(
        (
            "business_profile_update",
            "settings_dashboard_update",
            "expected_account_str",
        ),
        (
            ({}, {}, "dj-stripe"),
            ({}, {"display_name": "some display name"}, "some display name"),
            (
                {"name": "some business name"},
                {"display_name": ""},
                "some business name",
            ),
            ({"name": ""}, {"display_name": ""}, "<id=acct_1032D82eZvKYlo2C>"),
        ),
    )
    @patch("stripe.Account.retrieve", autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED)
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_LOGO),
        autospec=True,
    )
    def test_account_str(
        self,
        fileupload_retrieve_mock,
        account_retrieve_mock,
        business_profile_update,
        settings_dashboard_update,
        expected_account_str,
    ):
        fake_account = deepcopy(FAKE_ACCOUNT)
        fake_account["business_profile"].update(business_profile_update)
        fake_account["settings"]["dashboard"].update(settings_dashboard_update)
        account_retrieve_mock.return_value = fake_account
        account = Account.get_default_account()

        assert str(account) == expected_account_str

    @patch("stripe.Account.retrieve", autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED)
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_LOGO),
        autospec=True,
    )
    def test__str__null_settings_null_business_profile(
        self,
        fileupload_retrieve_mock,
        account_retrieve_mock,
    ):
        """Test that __str__ doesn't crash when settings and business_profile are NULL."""
        fake_account = deepcopy(FAKE_ACCOUNT)
        fake_account["settings"] = None
        fake_account["business_profile"] = None
        account_retrieve_mock.return_value = fake_account

        account = Account.sync_from_stripe_data(fake_account)
        assert str(account) == "<id=acct_1032D82eZvKYlo2C>"


class TestAccountRestrictedKeys(TestCase):
    @override_settings(
        STRIPE_TEST_SECRET_KEY="rk_test_blah",
        STRIPE_TEST_PUBLIC_KEY="pk_test_foo",
        STRIPE_LIVE_MODE=False,
    )
    @patch("stripe.Account.retrieve", autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED)
    def test_account_str_restricted_key(self, account_retrieve_mock):
        """
        Test that we do not attempt to retrieve account ID with restricted keys.
        """
        assert djstripe_settings.STRIPE_SECRET_KEY == "rk_test_blah"

        account = Account.get_default_account()

        assert account is None
        account_retrieve_mock.assert_not_called()


@pytest.mark.parametrize(
    "mock_account_id, other_mock_account_id, expected_stripe_account",
    (
        ("acct_fakefakefakefake001", None, "acct_fakefakefakefake001"),
        (
            "acct_fakefakefakefake001",
            "acct_fakefakefakefake002",
            "acct_fakefakefakefake002",
        ),
    ),
)
@patch(
    target="djstripe.models.connect.StripeModel._create_from_stripe_object",
    autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
)
def test_account__create_from_stripe_object(
    mock_super__create_from_stripe_object,
    mock_account_id,
    other_mock_account_id,
    expected_stripe_account,
):
    """Ensure that we are setting the ID value correctly."""
    mock_data = {"id": mock_account_id}
    Account._create_from_stripe_object(
        data=mock_data, stripe_account=other_mock_account_id
    )

    mock_super__create_from_stripe_object.assert_called_once_with(
        data=mock_data,
        current_ids=None,
        pending_relations=None,
        save=True,
        stripe_account=expected_stripe_account,
    )
