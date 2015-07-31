"""
.. module:: dj-stripe.tests.test_invoice
   :synopsis: dj-stripe Invoice Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
from datetime import timedelta
from decimal import Decimal

from django.test.testcases import TestCase
from django.utils import timezone

from mock import patch
from djstripe.event_handlers import invoice_webhook_handler

from djstripe.models import Customer, Invoice, Charge, Event


FAKE_INVOICE = {
    "date": 1432327437,
    "id": "in_xxxxxxxxxxxxxxx",
    "period_start": 1429735292,
    "period_end": 1432327292,
    "lines": {
        "object": "list",
        "total_count": 1,
        "has_more": False,
        "url": "/v1/invoices/in_xxxxxxxxxxxxxxx/lines",
        "data": [{
            "id": "sub_xxxxxxxxxxxxxxx",
            "object": "line_item",
            "type": "subscription",
            "livemode": True,
            "amount": 995,
            "currency": "usd",
            "proration": False,
            "period": {"start": 1432327292, "end": 1435005692},
            "subscription": None,
            "quantity": 1,
            "plan": {
                "interval": "month",
                "name": "Basic",
                "created": 1429616163,
                "amount": 995,
                "currency": "usd",
                "id": "test_id",
                "object": "plan",
                "livemode": True,
                "interval_count": 1,
                "trial_period_days": None,
                "metadata": {},
                "statement_descriptor": "Basic"
            },
            "description": None,
            "discountable": True,
            "metadata": {}
        }]
    },
    "subtotal": 995,
    "total": 995,
    "customer": "cus_xxxxxxxxxxxxxxx",
    "object": "invoice",
    "attempted": False,
    "closed": False,
    "forgiven": False,
    "paid": False,
    "livemode": True,
    "attempt_count": 0,
    "amount_due": 995,
    "currency": "usd",
    "starting_balance": 0,
    "ending_balance": None,
    "next_payment_attempt": 1432331037,
    "webhooks_delivered_at": None,
    "charge": None,
    "discount": None,
    "application_fee": None,
    "subscription": "sub_xxxxxxxxxxxxxxx",
    "tax_percent": None,
    "tax": None,
    "metadata": {},
    "statement_descriptor": None,
    "description": None,
    "receipt_number": None,
}


class InvoiceTest(TestCase):

    def setUp(self):
        self.customer = Customer.objects.create(stripe_id="cus_xxxxxxxxxxxxxxx")
        self.invoice = Invoice.objects.create(stripe_id="inv_xxxxxxxx123456",
                                              customer=self.customer,
                                              period_start=timezone.now(),
                                              period_end=timezone.now() + timedelta(days=5),
                                              subtotal=Decimal("35.00"),
                                              total=Decimal("50.00"),
                                              date=timezone.now(),
                                              charge="crg_xxxxxxxxx12345")

    def test_tostring(self):
        self.assertEquals("<total=50.00, paid=False, stripe_id=inv_xxxxxxxx123456>", str(self.invoice))

    @patch("stripe.Invoice.retrieve")
    def test_retry_true(self, invoice_retrieve_mock):
        return_value = self.invoice.retry()

        invoice_retrieve_mock.assert_called_once_with(self.invoice.stripe_id)
        self.assertTrue(return_value)

    @patch("stripe.Invoice.retrieve")
    def test_retry_false(self, invoice_retrieve_mock):
        invoice = self.invoice
        invoice.pk = None
        invoice.stripe_id = "inv_xxxxxxxx1234567"
        invoice.paid = True
        invoice.save()

        return_value = invoice.retry()

        self.assertFalse(invoice_retrieve_mock.called)
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
        invoice = Invoice.sync_from_stripe_data(FAKE_INVOICE)

        self.assertEqual("in_xxxxxxxxxxxxxxx", invoice.stripe_id)
        self.assertEqual(False, invoice.attempted)
        self.assertEqual(False, invoice.closed)
        self.assertEqual(False, invoice.paid)
        self.assertEqual(Decimal("9.95"), invoice.subtotal)
        self.assertEqual(Decimal("9.95"), invoice.total)
        self.assertEqual("", invoice.charge)

        self.assertEqual(1, invoice.items.count())
        invoice_item = invoice.items.all()[0]

        self.assertEqual("sub_xxxxxxxxxxxxxxx", invoice_item.stripe_id)
        self.assertEqual(Decimal("9.95"), invoice_item.amount)
        self.assertEqual("usd", invoice_item.currency)
        self.assertEqual(False, invoice_item.proration)
        self.assertEqual("", invoice_item.description)
        self.assertEqual("subscription", invoice_item.line_type)
        self.assertEqual("test", invoice_item.plan)
        self.assertEqual(1, invoice_item.quantity)

        # period_end is determined by latest invoice_item
        self.assertEqual(invoice_item.period_end, invoice.period_end)

        # Update invoice
        Invoice.sync_from_stripe_data(FAKE_INVOICE)

    def test_sync_from_stripe_data_no_plan(self):
        FAKE_INVOICE_NO_PLAN = deepcopy(FAKE_INVOICE)
        FAKE_INVOICE_NO_PLAN["id"] = "in_yyyyyyyyyyyyyyy"
        FAKE_INVOICE_NO_PLAN["subscription"] = "sub_yyyyyyyyyyyyyyy"
        FAKE_INVOICE_NO_PLAN["lines"]["data"][0]["id"] = "sub_yyyyyyyyyyyyyyy"

        FAKE_INVOICE_NO_PLAN["lines"]["data"][0]["plan"] = None

        invoice = Invoice.sync_from_stripe_data(FAKE_INVOICE_NO_PLAN)
        self.assertEqual(1, invoice.items.count())
        invoice_item = invoice.items.all()[0]

        self.assertEqual("", invoice_item.plan)

    @patch("djstripe.models.Charge.send_receipt")
    @patch("djstripe.models.Customer.record_charge")
    def test_sync_from_stripe_data_with_charge(self, record_charge_mock, send_receipt_mock):
        record_charge_mock.return_value = Charge(customer=self.customer)

        FAKE_INVOICE_WITH_CHARGE = deepcopy(FAKE_INVOICE)
        FAKE_INVOICE_WITH_CHARGE["id"] = "in_zzzzzzzzzzzzzzz"
        FAKE_INVOICE_WITH_CHARGE["subscription"] = "sub_zzzzzzzzzzzzzzz"
        FAKE_INVOICE_WITH_CHARGE["lines"]["data"][0]["id"] = "sub_zzzzzzzzzzzzzzz"

        FAKE_INVOICE_WITH_CHARGE["charge"] = "taco"

        Invoice.sync_from_stripe_data(FAKE_INVOICE_WITH_CHARGE)
        record_charge_mock.assert_called_once_with("taco")
        send_receipt_mock.assert_called_once_with()

    @patch("djstripe.models.Charge.send_receipt")
    @patch("djstripe.models.Customer.record_charge", return_value=Charge())
    def test_sync_from_stripe_data_with_charge_no_receipt(self, record_charge_mock, send_receipt_mock):
        record_charge_mock.return_value = Charge(customer=self.customer)

        FAKE_INVOICE_WITH_CHARGE = deepcopy(FAKE_INVOICE)
        FAKE_INVOICE_WITH_CHARGE["id"] = "in_zzzzzzzzzzzzzzz1"
        FAKE_INVOICE_WITH_CHARGE["subscription"] = "sub_zzzzzzzzzzzzzzz1"
        FAKE_INVOICE_WITH_CHARGE["lines"]["data"][0]["id"] = "sub_zzzzzzzzzzzzzzz1"

        FAKE_INVOICE_WITH_CHARGE["charge"] = "taco1"

        Invoice.sync_from_stripe_data(FAKE_INVOICE_WITH_CHARGE, send_receipt=False)
        record_charge_mock.assert_called_once_with("taco1")
        self.assertFalse(send_receipt_mock.called)

    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("stripe.Invoice.retrieve", return_value="lock")
    def test_handle_event_payment_failed(self, invoice_retrieve_mock, sync_invoice_mock):
        fake_event = Event(kind="invoice.payment_failed", validated_message={"data": {"object": {"id": "door"}}})

        invoice_webhook_handler(fake_event, fake_event.message["data"], "invoice", "payment_failed")

        invoice_retrieve_mock.assert_called_once_with("door")
        sync_invoice_mock.assert_called_once_with("lock", send_receipt=True)

    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("stripe.Invoice.retrieve", return_value="key")
    def test_handle_event_payment_succeeded(self, invoice_retrieve_mock, sync_invoice_mock):
        fake_event = Event(kind="invoice.payment_succeeded", validated_message={"data": {"object": {"id": "lock"}}})

        invoice_webhook_handler(fake_event, fake_event.message["data"], "invoice", "payment_failed")

        invoice_retrieve_mock.assert_called_once_with("lock")
        sync_invoice_mock.assert_called_once_with("key", send_receipt=True)
