"""
.. module:: dj-stripe.tests.test_invoice
   :synopsis: dj-stripe Invoice Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

"""

from copy import deepcopy

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test.testcases import TestCase
from mock import patch, ANY

from djstripe.models import Customer, Invoice, Account, UpcomingInvoice, \
    Subscription, Plan
from djstripe.models import InvalidRequestError

from tests import FAKE_INVOICE, FAKE_CHARGE, FAKE_CUSTOMER, FAKE_SUBSCRIPTION, FAKE_PLAN, FAKE_INVOICEITEM_II, FAKE_UPCOMING_INVOICE


class InvoiceTest(TestCase):

    def setUp(self):
        self.account = Account.objects.create()
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        self.customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_str(self, charge_retrieve_mock, subscription_retrive_mock, default_account_mock):
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
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_retry_true(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock, invoice_retrieve_mock):
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
    def test_retry_false(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock, invoice_retrieve_mock):
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

    @patch("djstripe.models.djstripe_settings", autospec=True)
    @patch("djstripe.models.Charge.send_receipt")
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_sync_send_emails_false(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock, send_receipt_mock, settings_fake):
        default_account_mock.return_value = self.account
        settings_fake.SEND_INVOICE_RECEIPT_EMAILS = False

        invoice_data = deepcopy(FAKE_INVOICE)
        Invoice.sync_from_stripe_data(invoice_data)

        self.assertFalse(send_receipt_mock.called)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_sync_no_subscription(self, charge_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock, default_account_mock):
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
    def test_invoice_with_subscription_invoice_items(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        items = invoice.invoiceitems.all()
        self.assertEquals(1, len(items))
        item_id = "{invoice_id}-{subscription_id}".format(invoice_id=invoice.stripe_id, subscription_id=FAKE_SUBSCRIPTION["id"])
        self.assertEquals(item_id, items[0].stripe_id)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_invoice_with_no_invoice_items(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"] = []
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNotNone(invoice.plan)  # retrieved from invoice item
        self.assertEquals(FAKE_PLAN["id"], invoice.plan.stripe_id)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_invoice_with_non_subscription_invoice_items(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"]["data"].append(deepcopy(FAKE_INVOICEITEM_II))
        invoice_data["lines"]["total_count"] += 1
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNotNone(invoice)
        self.assertEquals(2, len(invoice.invoiceitems.all()))

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_invoice_plan_from_invoice_items(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNotNone(invoice.plan)  # retrieved from invoice item
        self.assertEquals(FAKE_PLAN["id"], invoice.plan.stripe_id)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    def test_invoice_plan_from_subscription(self, charge_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"]["data"][0]["plan"] = None
        invoice = Invoice.sync_from_stripe_data(invoice_data)
        self.assertIsNotNone(invoice.plan)  # retrieved from subscription
        self.assertEquals(FAKE_PLAN["id"], invoice.plan.stripe_id)

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

        subscription_retrieve_mock.assert_called_once_with(api_key=ANY, expand=ANY, id=FAKE_SUBSCRIPTION["id"])
        plan_retrieve_mock.assert_not_called()

        items = invoice.invoiceitems.all()
        self.assertEquals(1, len(items))
        self.assertEquals(FAKE_SUBSCRIPTION["id"], items[0].stripe_id)

        self.assertIsNotNone(invoice.plan)
        self.assertEquals(FAKE_PLAN["id"], invoice.plan.stripe_id)

        invoice._invoiceitems = []
        items = invoice.invoiceitems.all()
        self.assertEquals(0, len(items))
        self.assertIsNotNone(invoice.plan)

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Invoice.upcoming", return_value=deepcopy(FAKE_UPCOMING_INVOICE))
    def test_upcoming_invoice_with_subscription(self, invoice_upcoming_mock, subscription_retrieve_mock, plan_retrieve_mock):
        invoice = Invoice.upcoming(subscription=Subscription(stripe_id=FAKE_SUBSCRIPTION["id"]))
        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.stripe_id)
        self.assertIsNone(invoice.save())

        subscription_retrieve_mock.assert_called_once_with(api_key=ANY, expand=ANY, id=FAKE_SUBSCRIPTION["id"])
        plan_retrieve_mock.assert_not_called()

        self.assertIsNotNone(invoice.plan)
        self.assertEquals(FAKE_PLAN["id"], invoice.plan.stripe_id)

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Invoice.upcoming", return_value=deepcopy(FAKE_UPCOMING_INVOICE))
    def test_upcoming_invoice_with_subscription_plan(self, invoice_upcoming_mock, subscription_retrieve_mock, plan_retrieve_mock):
        invoice = Invoice.upcoming(subscription_plan=Plan(stripe_id=FAKE_PLAN["id"]))
        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.stripe_id)
        self.assertIsNone(invoice.save())

        subscription_retrieve_mock.assert_called_once_with(api_key=ANY, expand=ANY, id=FAKE_SUBSCRIPTION["id"])
        plan_retrieve_mock.assert_not_called()

        self.assertIsNotNone(invoice.plan)
        self.assertEquals(FAKE_PLAN["id"], invoice.plan.stripe_id)

    @patch("stripe.Invoice.upcoming", side_effect=InvalidRequestError("Nothing to invoice for customer", None))
    def test_no_upcoming_invoices(self, invoice_upcoming_mock):
        invoice = Invoice.upcoming()
        self.assertIsNone(invoice)

    @patch("stripe.Invoice.upcoming", side_effect=InvalidRequestError("Some other error", None))
    def test_upcoming_invoice_error(self, invoice_upcoming_mock):
        with self.assertRaises(InvalidRequestError):
            Invoice.upcoming()
