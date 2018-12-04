"""
dj-stripe Account Tests.
"""
from unittest.mock import patch

from django.test.testcases import TestCase

from djstripe.models import Account
from djstripe.settings import STRIPE_SECRET_KEY

from . import FAKE_ACCOUNT


class TestAccount(TestCase):
	@patch("stripe.Account.retrieve")
	def test_get_connected_account_from_token(self, account_retrieve_mock):
		account_retrieve_mock.return_value = FAKE_ACCOUNT

		Account.get_connected_account_from_token("fake_token")

		account_retrieve_mock.assert_called_once_with(api_key="fake_token")

	@patch("stripe.Account.retrieve")
	def test_get_default_account(self, account_retrieve_mock):
		account_retrieve_mock.return_value = FAKE_ACCOUNT

		Account.get_default_account()

		account_retrieve_mock.assert_called_once_with(api_key=STRIPE_SECRET_KEY)
