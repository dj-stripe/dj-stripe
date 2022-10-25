"""
dj-stripe Account Tests.
"""
from copy import deepcopy
from unittest.mock import call, patch

import pytest
import stripe
from django.conf import settings
from django.test.testcases import TestCase
from django.test.utils import override_settings

from djstripe.models import Account
from djstripe.models.api import APIKey
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


from .conftest import CreateAccountMixin


class TestAccount(CreateAccountMixin, AssertStripeFksMixin, TestCase):
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
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
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
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
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
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
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
    monkeypatch,
):
    """Test that API reject properly uses the passed in parameters."""

    def mock_account_retrieve(*args, **kwargs):
        return FAKE_PLATFORM_ACCOUNT

    monkeypatch.setattr(stripe.Account, "retrieve", mock_account_retrieve)

    # create a Stripe Platform Account
    FAKE_PLATFORM_ACCOUNT.create()

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
        stripe_version=djstripe_settings.STRIPE_API_VERSION,
        **extra_kwargs,
    )


@pytest.mark.stripe_api
class TestAccountSTRIPE:
    """Tests for dj-stripe Account model using Stripe."""

    def test_sync_from_stripe_data(self, platform_account_fixture, configure_settings):
        """Ensure sync_from_stripe_data() on Account model works as expected."""

        # Create Account on Stripe.
        account_json = stripe.Account.create(
            type="standard",
            country="US",
            email="jenny.standard.rosen@example.com",
            api_key=settings.STRIPE_TEST_SECRET_KEY,
        )
        try:
            account_instance = Account.sync_from_stripe_data(
                account_json, api_key=settings.STRIPE_TEST_SECRET_KEY
            )

            assert account_instance.id == account_json["id"]
            assert account_instance.type == account_json["type"]
            assert account_instance.email == account_json["email"]

        except:
            raise

        # deleted created Account
        finally:
            # try to delete
            stripe.Account.delete(
                account_json["id"], api_key=settings.STRIPE_TEST_SECRET_KEY
            )

    @pytest.mark.parametrize(
        "account",
        ["platform_account_fixture"],
    )
    def test__attach_objects_post_save_hook_livemode_valid_platform_account(
        self, account, request, platform_account_fixture, configure_settings
    ):
        """Ensure _attach_objects_post_save_hook() on Account model works as expected."""
        account_json, account_instance = request.getfixturevalue(account)

        # Invoke _attach_objects_post_save_hook()
        account_instance._attach_objects_post_save_hook(
            cls=Account, data=account_json, api_key=settings.STRIPE_SECRET_KEY
        )

        account_instance.refresh_from_db()

        # Platform Accounts have no livemode
        assert account_instance.livemode is None

    @pytest.mark.parametrize("livemode", [True, False, None])
    @pytest.mark.parametrize(
        "account",
        [
            "custom_account_fixture",
            "standard_account_fixture",
        ],
    )
    def test__attach_objects_post_save_hook_livemode_valid_connected_account(
        self, account, livemode, request, platform_account_fixture, configure_settings
    ):
        """Ensure _attach_objects_post_save_hook() on Account model works as expected."""
        account_json, account_instance = request.getfixturevalue(account)

        with patch(
            "djstripe.models.account.get_api_key_details_by_prefix",
            return_value=("some-secret-key", livemode),
        ) as mock_get_api_key_details_by_prefix:
            # Invoke _attach_objects_post_save_hook()
            account_instance._attach_objects_post_save_hook(
                cls=Account, data=account_json, api_key=settings.STRIPE_SECRET_KEY
            )

        mock_get_api_key_details_by_prefix.assert_called_once_with(
            settings.STRIPE_TEST_SECRET_KEY,
        )

        assert account_instance.livemode == livemode

    @pytest.mark.parametrize(
        "account",
        ["platform_account_fixture"],
    )
    def test__attach_objects_post_save_hook(
        self, account, request, platform_account_fixture, configure_settings
    ):
        """Ensure _attach_objects_post_save_hook() on Account model works as expected."""
        account_json, account_instance = request.getfixturevalue(account)

        assert account_instance.branding_icon is not None
        assert account_instance.branding_logo is not None

        with patch("djstripe.models.core.File") as mock_file:
            with patch.object(mock_file.return_value, "api_retrieve") as mock_retrieve:
                # Invoke _attach_objects_post_save_hook()
                account_instance._attach_objects_post_save_hook(
                    cls=Account, data=account_json, api_key=settings.STRIPE_SECRET_KEY
                )

        # one for Icon and one for Logo
        mock_retrieve.assert_has_calls(
            [
                call(
                    stripe_account=account_instance.id,
                    api_key=settings.STRIPE_TEST_SECRET_KEY,
                ),
                call(
                    stripe_account=account_instance.id,
                    api_key=settings.STRIPE_TEST_SECRET_KEY,
                ),
            ]
        )

    @pytest.mark.parametrize(
        "account",
        ["platform_account_fixture"],
    )
    def test__attach_objects_post_save_hook_invalid_permission_error(
        self, account, request, platform_account_fixture, configure_settings
    ):
        """Ensure _attach_objects_post_save_hook() on Account model raises Error as expected."""
        account_json, account_instance = request.getfixturevalue(account)

        assert account_instance.branding_icon is not None
        assert account_instance.branding_logo is not None

        with patch("djstripe.models.account.logger") as mock_logger:
            with patch("djstripe.models.core.File") as mock_file:
                with patch.object(
                    mock_file.return_value,
                    "api_retrieve",
                    side_effect=stripe.error.PermissionError,
                ) as mock_retrieve:
                    # Invoke _attach_objects_post_save_hook()
                    account_instance._attach_objects_post_save_hook(
                        cls=Account,
                        data=account_json,
                        api_key=settings.STRIPE_SECRET_KEY,
                    )

        mock_logger.warning.assert_has_calls(
            [
                call(
                    f"Cannot retrieve business branding icon for acct {account_instance.id} with the key."
                ),
                call(
                    f"Cannot retrieve business branding logo for acct {account_instance.id} with the key."
                ),
            ]
        )

    @pytest.mark.parametrize(
        "account",
        ["platform_account_fixture"],
    )
    def test__attach_objects_post_save_hook_invalid_invalid_request_error_unknown_exception(
        self, account, request, platform_account_fixture, configure_settings
    ):
        """Ensure _attach_objects_post_save_hook() on Account model raises Error as expected."""
        account_json, account_instance = request.getfixturevalue(account)

        assert account_instance.branding_icon is not None
        assert account_instance.branding_logo is not None

        with pytest.raises(stripe.error.InvalidRequestError) as exc:
            with patch("djstripe.models.core.File") as mock_file:
                with patch.object(
                    mock_file.return_value,
                    "api_retrieve",
                    side_effect=stripe.error.InvalidRequestError("error message", {}),
                ) as mock_retrieve:
                    # Invoke _attach_objects_post_save_hook()
                    account_instance._attach_objects_post_save_hook(
                        cls=Account,
                        data=account_json,
                        api_key=settings.STRIPE_SECRET_KEY,
                    )

        assert "error message" == exc.value._message

    @pytest.mark.parametrize(
        "account",
        ["platform_account_fixture"],
    )
    def test__attach_objects_post_save_hook_invalid_invalid_request_error_known_exception(
        self, account, request, platform_account_fixture, configure_settings
    ):
        """Ensure _attach_objects_post_save_hook() on Account model raises Error as expected."""
        account_json, account_instance = request.getfixturevalue(account)

        assert account_instance.branding_icon is not None
        assert account_instance.branding_logo is not None

        # No exception is raised
        with patch("djstripe.models.core.File") as mock_file:
            with patch.object(
                mock_file.return_value,
                "api_retrieve",
                side_effect=stripe.error.InvalidRequestError(
                    "a similar object exists in", {}
                ),
            ) as mock_retrieve:
                # Invoke _attach_objects_post_save_hook()
                account_instance._attach_objects_post_save_hook(
                    cls=Account, data=account_json, api_key=settings.STRIPE_SECRET_KEY
                )

    @pytest.mark.parametrize(
        "account",
        ["platform_account_fixture"],
    )
    def test__attach_objects_post_save_hook_invalid_authentication_error(
        self, account, request, platform_account_fixture, configure_settings
    ):
        """Ensure _attach_objects_post_save_hook() on Account model raises Error as expected."""
        account_json, account_instance = request.getfixturevalue(account)

        assert account_instance.branding_icon is not None
        assert account_instance.branding_logo is not None

        with patch("djstripe.models.account.logger") as mock_logger:
            with patch("djstripe.models.core.File") as mock_file:
                with patch.object(
                    mock_file.return_value,
                    "api_retrieve",
                    side_effect=stripe.error.AuthenticationError,
                ) as mock_retrieve:
                    # Invoke _attach_objects_post_save_hook()
                    account_instance._attach_objects_post_save_hook(
                        cls=Account,
                        data=account_json,
                        api_key=settings.STRIPE_SECRET_KEY,
                    )

        mock_logger.warning.assert_not_called()

    @pytest.mark.parametrize(
        "account",
        [
            "custom_account_fixture",
            "standard_account_fixture",
        ],
    )
    def test__attach_objects_post_save_hook_without_icon_and_logo(
        self, account, request, platform_account_fixture, configure_settings
    ):
        """Ensure _attach_objects_post_save_hook() on Account model works as expected."""
        account_json, account_instance = request.getfixturevalue(account)

        assert account_instance.branding_icon is None
        assert account_instance.branding_logo is None

        with patch("djstripe.models.core.File") as mock_file:
            with patch.object(mock_file.return_value, "api_retrieve") as mock_retrieve:
                # Invoke _attach_objects_post_save_hook()
                account_instance._attach_objects_post_save_hook(
                    cls=Account, data=account_json, api_key=settings.STRIPE_SECRET_KEY
                )

        mock_retrieve.assert_not_called()

    @pytest.mark.parametrize("livemode", [False, True])
    @pytest.mark.parametrize(
        "account",
        [
            "platform_account_fixture",
            "custom_account_fixture",
            "standard_account_fixture",
        ],
    )
    def test_get_stripe_dashboard_url(
        self, account, livemode, request, platform_account_fixture, configure_settings
    ):
        """Ensure get_stripe_dashboard_url() on Account model works as expected."""
        # second entry is the model instance
        djstripe_account = request.getfixturevalue(account)[1]
        # Platform accounts do not have a livemode
        if account != "platform_account_fixture":
            djstripe_account.livemode = livemode
            djstripe_account.save()
            djstripe_account.refresh_from_db()

        assert djstripe_account.get_stripe_dashboard_url() == (
            f"https://dashboard.stripe.com/{djstripe_account.id}/"
            f"{'test/' if not djstripe_account.livemode else ''}dashboard"
        )

    @pytest.mark.parametrize(
        "account",
        [
            "custom_account_fixture",
            "standard_account_fixture",
        ],
    )
    def test_get_default_account_null_logo(
        self, account, request, platform_account_fixture, configure_settings
    ):
        """Ensure null icons and logos get populated as expected."""
        # second entry is the model instance
        djstripe_account = request.getfixturevalue(account)[1]

        assert djstripe_account.branding_icon is None
        assert djstripe_account.branding_logo is None

    @pytest.mark.parametrize(
        "account",
        [
            "platform_account_fixture",
            "custom_account_fixture",
            "standard_account_fixture",
        ],
    )
    def test__find_owner_account(
        self, account, request, platform_account_fixture, configure_settings
    ):
        """Ensure the expected Owner account is returned."""
        # second entry is the model instance
        account = request.getfixturevalue(account)[1]
        assert account.djstripe_owner_account.id == platform_account_fixture[1].id

    def test_get_default_account(self, platform_account_fixture, configure_settings):
        """Ensure the expected default account is returned."""
        account = Account.get_default_account(api_key=settings.STRIPE_SECRET_KEY)

        assert account.id == "acct_1ItQ7cJSZQVUcJYg"

        assert account.djstripe_owner_account == account
        assert account.djstripe_owner_account == platform_account_fixture[1]

    @pytest.mark.parametrize(
        "business_profile_update, expected_business_url",
        [
            ({}, ""),
            ({"url": ""}, ""),
            (
                {"url": "https://some-random-url/"},
                "https://some-random-url/",
            ),
        ],
    )
    def test_business_url(
        self,
        business_profile_update,
        expected_business_url,
        platform_account_fixture,
        configure_settings,
    ):
        """Ensure Account model's business_url property works as expected."""
        account = platform_account_fixture[1]
        account.business_profile = business_profile_update
        account.save()
        account.refresh_from_db()
        assert account.business_url == expected_business_url

    def test_branding_logo(self, platform_account_fixture):
        """Ensure Account model's branding_logo property works as expected."""
        account = platform_account_fixture[1]
        assert account.branding_logo.id == "file_1J423CJSZQVUcJYg7AsfwjcQ"

    def test_branding_icon(self, platform_account_fixture):
        """Ensure Account model's branding_icon property works as expected."""
        account = platform_account_fixture[1]
        assert account.branding_icon.id == "file_1J422OJSZQVUcJYgLYKEC9w6"

    @pytest.mark.parametrize(
        "business_profile_update, settings_dashboard_update, expected_account_str",
        [
            ({}, {}, "<id=acct_1ItQ7cJSZQVUcJYg>"),
            ({}, {"display_name": "some display name"}, "some display name"),
            (
                {"name": "some business name"},
                {"display_name": ""},
                "some business name",
            ),
            ({"name": ""}, {"display_name": ""}, "<id=acct_1ItQ7cJSZQVUcJYg>"),
        ],
    )
    def test_account_str(
        self,
        business_profile_update,
        settings_dashboard_update,
        expected_account_str,
        platform_account_fixture,
        configure_settings,
    ):
        """Ensure Account model's string representation is as expected."""
        account = Account.get_default_account(api_key=settings.STRIPE_SECRET_KEY)
        account.business_profile = business_profile_update
        account.settings["dashboard"] = settings_dashboard_update
        account.save()
        account.refresh_from_db()
        assert str(account) == expected_account_str

    @pytest.mark.parametrize("extra_kwargs", ({"reason": "fraud"}, {"reason": "other"}))
    def test_api_reject(
        self,
        custom_account_func_fixture,
        extra_kwargs,
        platform_account_fixture,
        configure_settings,
    ):
        """Test to ensure correct Account gets rejected."""
        account_json, account_instance = custom_account_func_fixture

        # assert "rejected" does not exist
        assert "rejected" not in account_json["requirements"]["disabled_reason"]

        # invoke api_reject()
        account_rejected = account_instance.api_reject(
            stripe_account=platform_account_fixture[1].id,
            api_key=settings.STRIPE_TEST_SECRET_KEY,
            **extra_kwargs,
        )

        assert account_rejected["charges_enabled"] is False
        assert account_rejected["payouts_enabled"] is False
        assert (
            account_rejected["requirements"]["disabled_reason"]
            == f"rejected.{extra_kwargs['reason']}"
        )

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
    def test_account__create_from_stripe_object(
        self,
        mock_account_id,
        other_mock_account_id,
        expected_stripe_account,
        platform_account_fixture,
        configure_settings,
    ):
        """Ensure that we are setting the ID value correctly."""
        mock_data = {"id": mock_account_id}
        with patch(
            "djstripe.models.connect.StripeModel._create_from_stripe_object"
        ) as mock_super__create_from_stripe_object:
            Account._create_from_stripe_object(
                data=mock_data,
                stripe_account=other_mock_account_id,
                api_key=settings.STRIPE_SECRET_KEY,
            )

        mock_super__create_from_stripe_object.assert_called_once_with(
            data=mock_data,
            current_ids=None,
            pending_relations=None,
            save=True,
            stripe_account=expected_stripe_account,
            api_key=settings.STRIPE_SECRET_KEY,
        )

    @pytest.mark.parametrize(
        "account",
        [
            "platform_account_fixture",
            "custom_account_fixture",
            "standard_account_fixture",
        ],
    )
    def test_get_or_retrieve_for_api_key_djstripe_owner_account_exists(
        self, account, request, platform_account_fixture, configure_settings
    ):
        """Ensure that djstripe_owner_account is returned correctly when it already exists on the api_key."""

        new_account = Account.get_or_retrieve_for_api_key(
            settings.STRIPE_TEST_SECRET_KEY
        )
        assert (
            platform_account_fixture[1].djstripe_owner_account
            == new_account.djstripe_owner_account
        )

    @pytest.mark.parametrize(
        "account",
        [
            "platform_account_fixture",
            "custom_account_fixture",
            "standard_account_fixture",
        ],
    )
    def test_get_or_retrieve_for_api_key_djstripe_owner_account_does_not_exist(
        self, account, request, platform_account_fixture, configure_settings
    ):
        """Ensure that djstripe_owner_account is returned correctly when it doesn't already exist on the api_key."""

        # second entry is the model instance
        account = request.getfixturevalue(account)[1]
        api_key_instance = APIKey.objects.get(secret=settings.STRIPE_TEST_SECRET_KEY)
        api_key_instance.djstripe_owner_account = None
        api_key_instance.save()

        with patch(
            "djstripe.models.api.APIKey.objects.get_or_create_by_api_key",
            return_value=(api_key_instance, False),
        ):
            new_account = Account.get_or_retrieve_for_api_key(
                settings.STRIPE_TEST_SECRET_KEY
            )

        assert (
            platform_account_fixture[1].djstripe_owner_account
            == new_account.djstripe_owner_account
        )

    @pytest.mark.parametrize(
        "account, livemode",
        [
            ("platform_account_fixture", None),
            ("custom_account_fixture", False),
            ("standard_account_fixture", False),
        ],
    )
    def test_get_default_api_key(
        self,
        account,
        livemode,
        request,
        platform_account_fixture,
        configure_settings,
    ):
        """Ensure that api_key gets retrieved correctly."""
        # second entry is the model instance
        account = request.getfixturevalue(account)[1]

        assert (
            account.get_default_api_key(livemode=livemode)
            == settings.STRIPE_TEST_SECRET_KEY
        )
        assert account.get_default_api_key() == settings.STRIPE_TEST_SECRET_KEY
