"""
dj-stripe Account Tests.
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.test.testcases import TestCase

from djstripe.models import Account
from djstripe.settings import STRIPE_SECRET_KEY

from . import (
    FAKE_ACCOUNT,
    FAKE_FILEUPLOAD_ICON,
    FAKE_FILEUPLOAD_LOGO,
    IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    AssertStripeFksMixin,
)


class TestAccount(AssertStripeFksMixin, TestCase):
    @patch("stripe.Account.retrieve", autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED)
    @patch(
        "stripe.FileUpload.retrieve",
        side_effect=[deepcopy(FAKE_FILEUPLOAD_ICON), deepcopy(FAKE_FILEUPLOAD_LOGO)],
        autospec=True,
    )
    def test_get_connected_account_from_token(
        self, fileupload_retrieve_mock, account_retrieve_mock
    ):
        account_retrieve_mock.return_value = deepcopy(FAKE_ACCOUNT)

        account = Account.get_connected_account_from_token("fake_token")

        account_retrieve_mock.assert_called_once_with(api_key="fake_token")

        self.assert_fks(account, expected_blank_fks={})

    @patch("stripe.Account.retrieve", autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED)
    @patch(
        "stripe.FileUpload.retrieve",
        side_effect=[deepcopy(FAKE_FILEUPLOAD_ICON), deepcopy(FAKE_FILEUPLOAD_LOGO)],
        autospec=True,
    )
    def test_get_default_account(self, fileupload_retrieve_mock, account_retrieve_mock):
        account_retrieve_mock.return_value = deepcopy(FAKE_ACCOUNT)

        account = Account.get_default_account()

        account_retrieve_mock.assert_called_once_with(api_key=STRIPE_SECRET_KEY)

        self.assertGreater(len(account.business_profile), 0)
        self.assertGreater(len(account.settings), 0)

        self.assertEqual(account.branding_icon.id, FAKE_FILEUPLOAD_ICON["id"])
        self.assertEqual(account.branding_logo.id, FAKE_FILEUPLOAD_LOGO["id"])

        self.assertEqual(account.settings["branding"]["icon"], account.branding_icon.id)
        self.assertEqual(account.settings["branding"]["logo"], account.branding_logo.id)

        self.assertNotEqual(account.branding_logo.id, account.branding_icon.id)

        self.assert_fks(account, expected_blank_fks={})

    @patch("stripe.Account.retrieve", autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED)
    @patch(
        "stripe.FileUpload.retrieve",
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

        account_retrieve_mock.assert_called_once_with(api_key=STRIPE_SECRET_KEY)

        self.assert_fks(
            account,
            expected_blank_fks={
                "djstripe.Account.branding_logo",
                "djstripe.Account.branding_icon",
            },
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("business_profile_update", "settings_dashboard_update", "expected_account_str"),
    (
        ({}, {}, "dj-stripe"),
        ({}, {"display_name": "some display name"}, "some display name"),
        ({"name": "some business name"}, {"display_name": ""}, "some business name"),
        ({"name": ""}, {"display_name": ""}, "<id=acct_1032D82eZvKYlo2C>"),
    ),
)
@patch("stripe.Account.retrieve", autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED)
@patch(
    "stripe.FileUpload.retrieve",
    return_value=deepcopy(FAKE_FILEUPLOAD_LOGO),
    autospec=True,
)
def test_account_str(
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


def test__str__null_settings_null_business_profile():
    """Test that __str__ doesn't crash when settings and business_profile are NULL."""
    account = Account()
    account.settings = None
    account.business_profile = None
    assert str(account) == "<id=>"
