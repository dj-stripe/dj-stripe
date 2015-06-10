"""
.. module:: dj-stripe.tests.test_invoice
   :synopsis: dj-stripe Invoice Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from datetime import timedelta
from decimal import Decimal

from django.test.testcases import TestCase
from django.utils import timezone

from mock import patch

from djstripe.models import Customer, Invoice


class InvoiceTest(TestCase):

    def setUp(self):
        self.customer = Customer.objects.create()
        self.invoice = Invoice.objects.create(stripe_id="inv_xxxxxxxx123456",
                                              customer=self.customer,
                                              period_start=timezone.now(),
                                              period_end=timezone.now() + timedelta(days=5),
                                              subtotal=Decimal("35.00"),
                                              total=Decimal("50.00"),
                                              date=timezone.now(),
                                              charge="crg_xxxxxxxxx12345")

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
