"""
.. module:: dj-stripe.tests.test_invoice
   :synopsis: dj-stripe Invoice Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from copy import deepcopy

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test.testcases import TestCase
from mock import ANY, patch

from djstripe.models import Account, InvalidRequestError, Invoice, Plan, Subscription, UpcomingInvoice

from . import (
    FAKE_CHARGE, FAKE_CUSTOMER, FAKE_INVOICE, FAKE_INVOICEITEM_II, FAKE_PLAN, FAKE_SUBSCRIPTION, FAKE_UPCOMING_INVOICE
)


class InvoiceTest(TestCase):

    def setUp(self):
        self.account = Account.objects.create()
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_str(self, charge_retrieve_mock, subscription_retrive_mock, default_account_mock):
        default_account_mock.return_value = self.account
        invoice = Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))
        self.assertEqual(invoice.get_stripe_dashboard_url(), self.customer.get_stripe_dashboard_url())

        self.assertEqual(
            "<amount_due={amount_due}, date={date}, status={status}, stripe_id={stripe_id}>".format(
                amount_due=invoice.amount_due,
                date=invoice.date,
                status=invoice.status,
                stripe_id=invoice.stripe_id
            ),
            str(invoice)
        )

    @patch("stripe.Invoice.retrieve")
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_retry_true(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock,
                        invoice_retrieve_mock):
        default_account_mock.return_value = self.account

        fake_invoice = deepcopy(FAKE_INVOICE)
        fake_invoice.update({"paid": False, "closed": False})
        invoice_retrieve_mock.return_value = fake_invoice

        invoice = Invoice.sync_from_stripe_data(fake_invoice)
        return_value = invoice.retry()

        invoice_retrieve_mock.assert_called_once_with(id=invoice.stripe_id, api_key=settings.STRIPE_SECRET_KEY,
                                                      expand=None)
        self.assertTrue(return_value)

    @patch("stripe.Invoice.retrieve")
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_retry_false(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock,
                         invoice_retrieve_mock):
        default_account_mock.return_value = self.account

        fake_invoice = deepcopy(FAKE_INVOICE)
        invoice_retrieve_mock.return_value = fake_invoice

        invoice = Invoice.sync_from_stripe_data(fake_invoice)
        return_value = invoice.retry()

        self.assertFalse(invoice_retrieve_mock.called)
        self.assertFalse(return_value)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_status_paid(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice = Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        self.assertEqual(Invoice.STATUS_PAID, invoice.status)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_status_open(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data.update({"paid": False, "closed": False})
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertEqual(Invoice.STATUS_OPEN, invoice.status)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_status_forgiven(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data.update({"paid": False, "closed": False, "forgiven": True})
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertEqual(Invoice.STATUS_FORGIVEN, invoice.status)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_status_closed(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data.update({"paid": False})
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertEqual(Invoice.STATUS_CLOSED, invoice.status)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_sync_no_subscription(self, charge_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock,
                                  default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data.update({"subscription": None})
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertEqual(None, invoice.subscription)

        charge_retrieve_mock.assert_called_once_with(api_key=ANY, expand=ANY, id=FAKE_CHARGE["id"])
        plan_retrieve_mock.assert_called_once_with(api_key=ANY, expand=ANY, id=FAKE_PLAN["id"])

        subscription_retrieve_mock.assert_not_called()

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_invoice_with_subscription_invoice_items(self, charge_retrieve_mock, subscription_retrieve_mock,
                                                     default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        items = invoice.invoiceitems.all()
        self.assertEqual(1, len(items))
        item_id = "{invoice_id}-{subscription_id}".format(invoice_id=invoice.stripe_id,
                                                          subscription_id=FAKE_SUBSCRIPTION["id"])
        self.assertEqual(item_id, items[0].stripe_id)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_invoice_with_no_invoice_items(self, charge_retrieve_mock, subscription_retrieve_mock,
                                           default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"] = []
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNotNone(invoice.plan)  # retrieved from invoice item
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.stripe_id)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_invoice_with_non_subscription_invoice_items(self, charge_retrieve_mock, subscription_retrieve_mock,
                                                         default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"]["data"].append(deepcopy(FAKE_INVOICEITEM_II))
        invoice_data["lines"]["total_count"] += 1
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNotNone(invoice)
        self.assertEqual(2, len(invoice.invoiceitems.all()))

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_invoice_plan_from_invoice_items(self, charge_retrieve_mock, subscription_retrieve_mock,
                                             default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNotNone(invoice.plan)  # retrieved from invoice item
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.stripe_id)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_invoice_plan_from_subscription(self, charge_retrieve_mock, subscription_retrieve_mock,
                                            default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"]["data"][0]["plan"] = None
        invoice = Invoice.sync_from_stripe_data(invoice_data)
        self.assertIsNotNone(invoice.plan)  # retrieved from subscription
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.stripe_id)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_invoice_without_plan(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"]["data"][0]["plan"] = None
        invoice_data["subscription"] = None
        invoice = Invoice.sync_from_stripe_data(invoice_data)
        self.assertIsNone(invoice.plan)

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Invoice.upcoming", return_value=deepcopy(FAKE_UPCOMING_INVOICE))
    def test_upcoming_invoice(self, invoice_upcoming_mock, subscription_retrieve_mock, plan_retrieve_mock):
        invoice = UpcomingInvoice.upcoming()
        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.stripe_id)
        self.assertIsNone(invoice.save())
        self.assertEqual(invoice.get_stripe_dashboard_url(), "")

        subscription_retrieve_mock.assert_called_once_with(api_key=ANY, expand=ANY, id=FAKE_SUBSCRIPTION["id"])
        plan_retrieve_mock.assert_not_called()

        items = invoice.invoiceitems.all()
        self.assertEqual(1, len(items))
        self.assertEqual(FAKE_SUBSCRIPTION["id"], items[0].stripe_id)

        # delete/update should do nothing
        self.assertEqual(invoice.invoiceitems.update(), 0)
        self.assertEqual(invoice.invoiceitems.delete(), 0)

        self.assertIsNotNone(invoice.plan)
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.stripe_id)

        invoice._invoiceitems = []
        items = invoice.invoiceitems.all()
        self.assertEqual(0, len(items))
        self.assertIsNotNone(invoice.plan)

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Invoice.upcoming", return_value=deepcopy(FAKE_UPCOMING_INVOICE))
    def test_upcoming_invoice_with_subscription(self, invoice_upcoming_mock, subscription_retrieve_mock,
                                                plan_retrieve_mock):
        invoice = Invoice.upcoming(subscription=Subscription(stripe_id=FAKE_SUBSCRIPTION["id"]))
        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.stripe_id)
        self.assertIsNone(invoice.save())

        subscription_retrieve_mock.assert_called_once_with(api_key=ANY, expand=ANY, id=FAKE_SUBSCRIPTION["id"])
        plan_retrieve_mock.assert_not_called()

        self.assertIsNotNone(invoice.plan)
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.stripe_id)

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Invoice.upcoming", return_value=deepcopy(FAKE_UPCOMING_INVOICE))
    def test_upcoming_invoice_with_subscription_plan(self, invoice_upcoming_mock, subscription_retrieve_mock,
                                                     plan_retrieve_mock):
        invoice = Invoice.upcoming(subscription_plan=Plan(stripe_id=FAKE_PLAN["id"]))
        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.stripe_id)
        self.assertIsNone(invoice.save())

        subscription_retrieve_mock.assert_called_once_with(api_key=ANY, expand=ANY, id=FAKE_SUBSCRIPTION["id"])
        plan_retrieve_mock.assert_not_called()

        self.assertIsNotNone(invoice.plan)
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.stripe_id)

    @patch("stripe.Invoice.upcoming", side_effect=InvalidRequestError("Nothing to invoice for customer", None))
    def test_no_upcoming_invoices(self, invoice_upcoming_mock):
        invoice = Invoice.upcoming()
        self.assertIsNone(invoice)

    @patch("stripe.Invoice.upcoming", side_effect=InvalidRequestError("Some other error", None))
    def test_upcoming_invoice_error(self, invoice_upcoming_mock):
        with self.assertRaises(InvalidRequestError):
            Invoice.upcoming()
