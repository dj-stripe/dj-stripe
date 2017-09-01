"""
.. module:: dj-stripe.tests.test_account
   :synopsis: dj-stripe Account Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.test.testcases import TestCase
from mock import patch

from djstripe.models import Account

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

        account_retrieve_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY)
