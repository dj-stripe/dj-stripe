"""
dj-stripe Account Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.test.testcases import TestCase

from djstripe.models import Account
from djstripe.settings import STRIPE_SECRET_KEY

from . import FAKE_ACCOUNT, FAKE_FILEUPLOAD, AssertStripeFksMixin


class TestAccount(AssertStripeFksMixin, TestCase):
	@patch("stripe.Account.retrieve")
	@patch("stripe.File.retrieve", return_value=deepcopy(FAKE_FILEUPLOAD))
	def test_get_connected_account_from_token(
		self, fileupload_retrieve_mock, account_retrieve_mock
	):
		account_retrieve_mock.return_value = FAKE_ACCOUNT

		account = Account.get_connected_account_from_token("fake_token")

		account_retrieve_mock.assert_called_once_with(api_key="fake_token")

		self.assert_fks(account, expected_blank_fks={})

	@patch("stripe.Account.retrieve")
	@patch("stripe.FileUpload.retrieve", return_value=deepcopy(FAKE_FILEUPLOAD))
	def test_get_default_account(self, fileupload_retrieve_mock, account_retrieve_mock):
		account_retrieve_mock.return_value = FAKE_ACCOUNT

		account = Account.get_default_account()

		account_retrieve_mock.assert_called_once_with(api_key=STRIPE_SECRET_KEY)

		self.assert_fks(account, expected_blank_fks={})

	@patch("stripe.Account.retrieve")
	@patch("stripe.FileUpload.retrieve", return_value=deepcopy(FAKE_FILEUPLOAD))
	def test_get_default_account_null_logo(
		self, fileupload_retrieve_mock, account_retrieve_mock
	):
		fake_account = deepcopy(FAKE_ACCOUNT)
		fake_account["business_logo"] = None
		account_retrieve_mock.return_value = fake_account

		account = Account.get_default_account()

		account_retrieve_mock.assert_called_once_with(api_key=STRIPE_SECRET_KEY)

		self.assert_fks(account, expected_blank_fks={"djstripe.Account.business_logo"})
