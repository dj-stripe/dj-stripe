"""
dj-stripe Account Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.test.testcases import TestCase

from djstripe.models import Account
from djstripe.settings import STRIPE_SECRET_KEY

from . import (
	FAKE_ACCOUNT, FAKE_FILEUPLOAD_ICON, FAKE_FILEUPLOAD_LOGO,
	IS_STATICMETHOD_AUTOSPEC_SUPPORTED, AssertStripeFksMixin
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

		with self.assertWarns(DeprecationWarning):
			self.assertEqual(account.business_logo.id, account.branding_icon.id)

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
