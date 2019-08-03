"""
dj-stripe Sync Method Tests.
"""
import contextlib
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test.testcases import TestCase
from stripe.error import InvalidRequestError

from djstripe.models import Customer
from djstripe.sync import sync_subscriber

from . import FAKE_CUSTOMER


@contextlib.contextmanager
def capture_stdout():
    import sys
    from io import StringIO

    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        yield sys.stdout
    finally:
        sys.stdout = old_stdout


class TestSyncSubscriber(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="123"
        )

    @patch("djstripe.models.Customer._sync_charges", autospec=True)
    @patch("djstripe.models.Customer._sync_invoices", autospec=True)
    @patch("djstripe.models.Customer._sync_subscriptions", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_success(
        self,
        stripe_customer_create_mock,
        api_retrieve_mock,
        _sync_subscriptions_mock,
        _sync_invoices_mock,
        _sync_charges_mock,
    ):

        sync_subscriber(self.user)
        self.assertEqual(1, Customer.objects.count())
        self.assertEqual(
            FAKE_CUSTOMER, Customer.objects.get(subscriber=self.user).api_retrieve()
        )

        _sync_subscriptions_mock.assert_called_once_with(Customer.objects.first())
        _sync_invoices_mock.assert_called_once_with(Customer.objects.first())
        _sync_charges_mock.assert_called_once_with(Customer.objects.first())

    @patch("djstripe.models.Customer._sync", autospec=True)
    @patch(
        "djstripe.models.Customer.api_retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_fail(
        self, stripe_customer_create_mock, api_retrieve_mock, _sync_mock
    ):
        _sync_mock.side_effect = InvalidRequestError("No such customer:", "blah")

        with capture_stdout() as stdout:
            sync_subscriber(self.user)

        self.assertEqual("ERROR: No such customer:", stdout.getvalue().strip())
