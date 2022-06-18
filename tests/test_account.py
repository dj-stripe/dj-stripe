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
    FAKE_CUSTOM_ACCOUNT,
    FAKE_EXPRESS_ACCOUNT,
    FAKE_FILEUPLOAD_ICON,
    FAKE_FILEUPLOAD_LOGO,
    FAKE_PLATFORM_ACCOUNT,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


class TestAccount(AssertStripeFksMixin, TestCase):
    @patch("stripe.Account.retrieve", autospec=True)
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
        autospec=True,
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
        autospec=True,
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
        self.assertEqual(account.djstripe_owner_account.id, FAKE_PLATFORM_ACCOUNT["id"])

    @patch(
        "stripe.Account.retrieve",
        autospec=True,
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
        autospec=True,
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
        autospec=True,
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

    @patch("stripe.Account.retrieve", autospec=True)
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

        account = Account.sync_from_stripe_data(fake_account)
        assert account.livemode is False

        fileupload_retrieve_mock.assert_called_with(
            id=fake_account["settings"]["branding"]["logo"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            expand=[],
            stripe_account=fake_account["id"],
        )

    @patch("stripe.Account.retrieve", autospec=True)
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

    @patch(
        "stripe.Account.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_ACCOUNT),
    )
    @patch(
        "stripe.File.retrieve",
        side_effect=[deepcopy(FAKE_FILEUPLOAD_ICON), deepcopy(FAKE_FILEUPLOAD_LOGO)],
        autospec=True,
    )
    def test_get_stripe_dashboard_url(
        self, fileupload_retrieve_mock, account_retrieve_mock
    ):
        fake_account = deepcopy(FAKE_ACCOUNT)
        account = Account.sync_from_stripe_data(fake_account)

        self.assertEqual(
            account.get_stripe_dashboard_url(),
            f"https://dashboard.stripe.com/{account.id}/"
            f"{'test/' if not account.livemode else ''}dashboard",
        )


class TestAccountMethods:
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
    @patch("stripe.Account.retrieve", autospec=True)
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

    @patch("stripe.Account.retrieve", autospec=True)
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

    @override_settings(
        STRIPE_SECRET_KEY="sk_live_XXXXXXXXXXXXXXXXXXXX5678",
        STRIPE_LIVE_MODE=True,
    )
    @pytest.mark.parametrize(
        "_account,is_platform",
        [
            (deepcopy(FAKE_ACCOUNT), False),
            (deepcopy(FAKE_CUSTOM_ACCOUNT), False),
            (deepcopy(FAKE_EXPRESS_ACCOUNT), False),
            (deepcopy(FAKE_PLATFORM_ACCOUNT), True),
        ],
    )
    @patch("stripe.Account.retrieve", autospec=True)
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_LOGO),
        autospec=True,
    )
    def test_livemode_populates_correctly_for_livemode(
        self,
        fileupload_retrieve_mock,
        account_retrieve_mock,
        _account,
        is_platform,
    ):
        fake_account = _account
        fake_account["settings"]["branding"]["icon"] = None
        account_retrieve_mock.return_value = fake_account

        platform_account = FAKE_PLATFORM_ACCOUNT.create()

        # Account.get_or_retrieve_for_api_key is called and since the passed in api_key doesn't have an owner acount,
        # key is refreshed and the current mocked _account is assigned as the owner account.
        # This essentially turns all these cases into Platform Account cases.
        # And that is why Account.get_or_retrieve_for_api_key is patched
        with patch.object(
            Account, "get_or_retrieve_for_api_key", return_value=platform_account
        ):

            account = Account.sync_from_stripe_data(
                fake_account, api_key=djstripe_settings.STRIPE_SECRET_KEY
            )
            assert account.djstripe_owner_account == platform_account

            if is_platform is True:
                assert account.livemode is None
            else:
                assert account.livemode is True

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_XXXXXXXXXXXXXXXXXXXX5678",
        STRIPE_LIVE_MODE=False,
    )
    @pytest.mark.parametrize(
        "_account,is_platform",
        [
            (deepcopy(FAKE_ACCOUNT), False),
            (deepcopy(FAKE_CUSTOM_ACCOUNT), False),
            (deepcopy(FAKE_EXPRESS_ACCOUNT), False),
            (deepcopy(FAKE_PLATFORM_ACCOUNT), True),
        ],
    )
    @patch("stripe.Account.retrieve", autospec=True)
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_LOGO),
        autospec=True,
    )
    def test_livemode_populates_correctly_for_testmode(
        self, fileupload_retrieve_mock, account_retrieve_mock, _account, is_platform
    ):
        fake_account = _account
        fake_account["settings"]["branding"]["icon"] = None
        account_retrieve_mock.return_value = fake_account

        platform_account = FAKE_PLATFORM_ACCOUNT.create()

        # Account.get_or_retrieve_for_api_key is called and since the passed in api_key doesn't have an owner acount,
        # key is refreshed and the current mocked _account is assigned as the owner account.
        # This essentially turns all these cases into Platform Account cases.
        # And that is why Account.get_or_retrieve_for_api_key is patched
        with patch.object(
            Account, "get_or_retrieve_for_api_key", return_value=platform_account
        ):

            account = Account.sync_from_stripe_data(
                fake_account, api_key=djstripe_settings.STRIPE_SECRET_KEY
            )
            assert account.djstripe_owner_account == platform_account

            if is_platform is True:
                assert account.livemode is None
            else:
                assert account.livemode is False


class TestAccountRestrictedKeys(TestCase):
    @override_settings(
        STRIPE_TEST_SECRET_KEY="rk_test_blah",
        STRIPE_TEST_PUBLIC_KEY="pk_test_foo",
        STRIPE_LIVE_MODE=False,
    )
    @patch("stripe.Account.retrieve", autospec=True)
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
    autospec=True,
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
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
    )


@pytest.mark.parametrize("stripe_account", (None, "acct_fakefakefakefake001"))
@pytest.mark.parametrize(
    "api_key, expected_api_key",
    (
        (None, djstripe_settings.STRIPE_SECRET_KEY),
        ("sk_fakefakefake01", "sk_fakefakefake01"),
    ),
)
@pytest.mark.parametrize("extra_kwargs", ({"reason": "fraud"}, {"reason": "other"}))
@patch(
    "stripe.Account.retrieve",
    autospec=True,
    return_value=deepcopy(FAKE_ACCOUNT),
)
@patch(
    "stripe.Account.reject",
)
@patch(
    "stripe.File.retrieve",
    side_effect=[deepcopy(FAKE_FILEUPLOAD_ICON), deepcopy(FAKE_FILEUPLOAD_LOGO)],
    autospec=True,
)
def test_api_reject(
    fileupload_retrieve_mock,
    account_reject_mock,
    account_retrieve_mock,
    extra_kwargs,
    api_key,
    expected_api_key,
    stripe_account,
):
    """Test that API reject properly uses the passed in parameters."""

    fake_account = deepcopy(FAKE_ACCOUNT)
    fake_account_rejected = deepcopy(FAKE_ACCOUNT)
    fake_account_rejected["charges_enabled"] = False
    fake_account_rejected["payouts_enabled"] = False
    account_reject_mock.return_value = fake_account_rejected

    account = Account.sync_from_stripe_data(fake_account)

    # invoke api_reject()
    account_rejected = account.api_reject(
        api_key=api_key, stripe_account=stripe_account, **extra_kwargs
    )

    assert account_rejected["charges_enabled"] is False
    assert account_rejected["payouts_enabled"] is False

    Account.stripe_class.reject.assert_called_once_with(
        account.id,
        api_key=expected_api_key,
        stripe_account=stripe_account or FAKE_PLATFORM_ACCOUNT["id"],
        **extra_kwargs,
    )
