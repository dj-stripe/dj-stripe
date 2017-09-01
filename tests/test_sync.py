"""
.. module:: dj-stripe.tests.test_sync
   :synopsis: dj-stripe Sync Method Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test.testcases import TestCase
from mock import patch
from stripe.error import InvalidRequestError

from djstripe.models import Customer
from djstripe.sync import sync_subscriber

from . import FAKE_CUSTOMER


class TestSyncSubscriber(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="123"
        )

    @patch("djstripe.models.Customer._sync_charges")
    @patch("djstripe.models.Customer._sync_invoices")
    @patch("djstripe.models.Customer._sync_subscriptions")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_sync_success(self, stripe_customer_create_mock, api_retrieve_mock, _sync_subscriptions_mock,
                          _sync_invoices_mock, _sync_charges_mock):

        sync_subscriber(self.user)
        self.assertEqual(1, Customer.objects.count())
        self.assertEqual(FAKE_CUSTOMER, Customer.objects.get(subscriber=self.user).api_retrieve())

        _sync_subscriptions_mock.assert_called_once_with()
        _sync_invoices_mock.assert_called_once_with()
        _sync_charges_mock.assert_called_once_with()

    @patch("djstripe.models.Customer._sync")
    @patch("djstripe.models.Customer.api_retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_sync_fail(self, stripe_customer_create_mock, api_retrieve_mock, _sync_mock):
        _sync_mock.side_effect = InvalidRequestError("No such customer:", "blah")

        sync_subscriber(self.user)

        self.assertEqual("ERROR: No such customer:", sys.stdout.getvalue().strip())
