"""
.. module:: dj-stripe.tests.test_invoice
   :synopsis: dj-stripe Invoice Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.conf import settings
from django.test.testcases import TestCase
from django.utils import timezone

from mock import patch

from djstripe.event_handlers import invoice_webhook_handler
from djstripe.models import Customer, Invoice, Charge, Event, Account

from . import FAKE_INVOICE


class InvoiceTest(TestCase):

    def setUp(self):
        self.customer = Customer.objects.create(stripe_id="cus_6lsBvm5rJ0zyHc")
        self.invoice = Invoice.objects.create(stripe_id="in_16YHls2eZvKYlo2CwwH968Mc",
                                              customer=self.customer,
                                              period_start=timezone.now(),
                                              period_end=timezone.now() + timedelta(days=5),
                                              subtotal=Decimal("35.00"),
                                              total=Decimal("50.00"),
                                              date=timezone.now(),
                                              charge="ch_16YIoj2eZvKYlo2CrPdYapBH")
        self.account = Account.objects.create()

    def test_tostring(self):
        self.assertEquals("<total=50.00, paid=False, stripe_id=in_16YHls2eZvKYlo2CwwH968Mc>", str(self.invoice))

    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("stripe.Invoice.retrieve", return_value=FAKE_INVOICE)
    def test_retry_true(self, invoice_retrieve_mock, invoice_sync_mock):
        return_value = self.invoice.retry()

        invoice_retrieve_mock.assert_called_once_with(id=self.invoice.stripe_id, api_key=settings.STRIPE_SECRET_KEY, expand=None)
        invoice_sync_mock.assert_called_once_with("fish")
        self.assertTrue(return_value)

    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("stripe.Invoice.retrieve")
    def test_retry_false(self, invoice_retrieve_mock, invoice_sync_mock):
        invoice = self.invoice
        invoice.pk = None
        invoice.stripe_id = "inv_xxxxxxxx1234567"
        invoice.paid = True
        invoice.save()

        return_value = invoice.retry()

        self.assertFalse(invoice_retrieve_mock.called)
        self.assertFalse(invoice_sync_mock.called)
        self.assertFalse(return_value)

    def test_status_open(self):
        status = self.invoice.status()
        self.assertEqual("Open", status)

    def test_status_paid(self):
        invoice = self.invoice
        invoice.pk = None
        invoice.stripe_id = "inv_xxxxxxxx12345678"
        invoice.paid = True
        invoice.save()

        status = invoice.status()
        self.assertEqual("Paid", status)

    def test_status_closed(self):
        invoice = self.invoice
        invoice.pk = None
        invoice.stripe_id = "inv_xxxxxxxx123456789"
        invoice.closed = True
        invoice.save()

        status = invoice.status()
        self.assertEqual("Closed", status)

    def test_sync_from_stripe_data(self):
        fake_invoice_no_charge = deepcopy(FAKE_INVOICE)
        fake_invoice_no_charge.pop("charge", None)

        invoice = Invoice.sync_from_stripe_data(fake_invoice_no_charge)

        self.assertEqual("in_16YHls2eZvKYlo2CwwH968Mc", invoice.stripe_id)
        self.assertEqual(True, invoice.attempted)
        self.assertEqual(True, invoice.closed)
        self.assertEqual(True, invoice.paid)
        self.assertEqual(Decimal("20"), invoice.subtotal)
        self.assertEqual(Decimal("20"), invoice.total)
        self.assertEqual(None, invoice.charge)

        self.assertEqual(1, invoice.items.count())
        invoice_item = invoice.items.all()[0]

        self.assertEqual("sub_6lsC8pt7IcFpjA", invoice_item.stripe_id)
        self.assertEqual(Decimal("20"), invoice_item.amount)
        self.assertEqual("usd", invoice_item.currency)
        self.assertEqual(False, invoice_item.proration)
        self.assertEqual("", invoice_item.description)
        self.assertEqual("subscription", invoice_item.line_type)
        self.assertEqual(None, invoice_item.plan)
        self.assertEqual(1, invoice_item.quantity)

        # period_end is determined by latest invoice_item
        self.assertEqual(invoice_item.period_end, invoice.period_end)

        # Update invoice
        Invoice.sync_from_stripe_data(fake_invoice_no_charge)

    def test_sync_from_stripe_data_no_customer(self):
        fake_invoice_no_customer = deepcopy(FAKE_INVOICE)
        fake_invoice_no_customer.pop("charge", None)
        fake_invoice_no_customer.pop("customer", None)

        with self.assertRaisesMessage(ValidationError, "A customer was not attached to this charge."):
            Invoice.sync_from_stripe_data(fake_invoice_no_customer)

    @patch("stripe.Invoice.retrieve")
    def test_sync_from_stripe_data_no_plan(self, invoice_retrieve_mock):
        fake_invoice_no_plan = deepcopy(FAKE_INVOICE)
        fake_invoice_no_plan.pop("charge", None)
        fake_invoice_no_plan["lines"]["data"][0]["plan"] = None

        invoice_retrieve_mock.return_value = fake_invoice_no_plan

        invoice = Invoice.sync_from_stripe_data(fake_invoice_no_plan)
        self.assertEqual(1, invoice.items.count())
        invoice_item = invoice.items.all()[0]

        self.assertEqual("", invoice_item.plan)

    @patch("djstripe.models.Charge.send_receipt")
    @patch("djstripe.models.Customer.record_charge")
    def test_sync_from_stripe_data_with_charge(self, record_charge_mock, send_receipt_mock):
        record_charge_mock.return_value = Charge(customer=self.customer)

        fake_invoice_with_charge = deepcopy(FAKE_INVOICE)
        fake_invoice_with_charge["charge"] = "taco"

        Invoice.sync_from_stripe_data(fake_invoice_with_charge)
        record_charge_mock.assert_called_once_with("taco")
        send_receipt_mock.assert_called_once_with()

    @patch("djstripe.models.Charge.send_receipt")
    @patch("djstripe.models.Customer.record_charge", return_value=Charge())
    def test_sync_from_stripe_data_with_charge_no_receipt(self, record_charge_mock, send_receipt_mock):
        record_charge_mock.return_value = Charge(customer=self.customer)

        fake_invoice_with_charge = deepcopy(FAKE_INVOICE)
        fake_invoice_with_charge["charge"] = "taco1"

        Invoice.sync_from_stripe_data(fake_invoice_with_charge, send_receipt=False)
        record_charge_mock.assert_called_once_with("taco1")
        self.assertFalse(send_receipt_mock.called)

    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("stripe.Invoice.retrieve", return_value="lock")
    def test_handle_event_payment_failed(self, invoice_retrieve_mock, sync_invoice_mock):
        fake_event = Event(type="invoice.payment_failed", valid=True, webhook_message={"data": {"object": {"id": "door"}}})

        invoice_webhook_handler(fake_event, fake_event.message["data"], "invoice", "payment_failed")

        invoice_retrieve_mock.assert_called_once_with(id="door", api_key=settings.STRIPE_SECRET_KEY, expand=None)
        sync_invoice_mock.assert_called_once_with("lock", send_receipt=True)

    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("stripe.Invoice.retrieve", return_value="key")
    def test_handle_event_payment_succeeded(self, invoice_retrieve_mock, sync_invoice_mock):
        fake_event = Event(type="invoice.payment_succeeded", valid=True, webhook_message={"data": {"object": {"id": "lock"}}})

        invoice_webhook_handler(fake_event, fake_event.message["data"], "invoice", "payment_failed")

        invoice_retrieve_mock.assert_called_once_with(id="lock", api_key=settings.STRIPE_SECRET_KEY, expand=None)
        sync_invoice_mock.assert_called_once_with("key", send_receipt=True)
