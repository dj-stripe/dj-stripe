"""
.. module:: dj-stripe.tests.test_invoice
   :synopsis: dj-stripe Invoice Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test.testcases import TestCase
from mock import patch

from djstripe.models import Customer, Invoice, Account
from tests import FAKE_INVOICE, FAKE_CHARGE, FAKE_CUSTOMER, FAKE_SUBSCRIPTION


class InvoiceTest(TestCase):

    def setUp(self):
        self.account = Account.objects.create()
        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_str(self, charge_retrieve_mock, customer_retrieve_mock, subscription_retrive_mock, default_account_mock):
        default_account_mock.return_value = self.account
        invoice = Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        self.assertEqual(str(invoice), "<amount_due={amount_due}, date={date}, status={status}, stripe_id={stripe_id}>".format(
            amount_due=invoice.amount_due,
            date=invoice.date,
            status=invoice.status,
            stripe_id=invoice.stripe_id
        ))

    @patch("stripe.Invoice.retrieve")
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_retry_true(self, charge_retrieve_mock, customer_retrieve_mock, subscription_retrieve_mock, default_account_mock, invoice_retrieve_mock):
        default_account_mock.return_value = self.account

        fake_invoice = deepcopy(FAKE_INVOICE)
        fake_invoice.update({"paid": False, "closed": False})
        invoice_retrieve_mock.return_value = fake_invoice

        invoice = Invoice.sync_from_stripe_data(fake_invoice)
        return_value = invoice.retry()

        invoice_retrieve_mock.assert_called_once_with(id=invoice.stripe_id, api_key=settings.STRIPE_SECRET_KEY, expand=None)
        self.assertTrue(return_value)

    @patch("stripe.Invoice.retrieve")
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_retry_false(self, charge_retrieve_mock, customer_retrieve_mock, subscription_retrieve_mock, default_account_mock, invoice_retrieve_mock):
        default_account_mock.return_value = self.account

        fake_invoice = deepcopy(FAKE_INVOICE)
        invoice_retrieve_mock.return_value = fake_invoice

        invoice = Invoice.sync_from_stripe_data(fake_invoice)
        return_value = invoice.retry()

        self.assertFalse(invoice_retrieve_mock.called)
        self.assertFalse(return_value)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_status_paid(self, charge_retrieve_mock, customer_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice = Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        self.assertEqual(Invoice.STATUS_PAID, invoice.status)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_status_open(self, charge_retrieve_mock, customer_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data.update({"paid": False, "closed": False})
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertEqual(Invoice.STATUS_OPEN, invoice.status)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_status_forgiven(self, charge_retrieve_mock, customer_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data.update({"paid": False, "closed": False, "forgiven": True})
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertEqual(Invoice.STATUS_FORGIVEN, invoice.status)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_status_closed(self, charge_retrieve_mock, customer_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data.update({"paid": False})
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertEqual(Invoice.STATUS_CLOSED, invoice.status)
