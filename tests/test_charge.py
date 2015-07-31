"""
.. module:: dj-stripe.tests.test_charge
   :synopsis: dj-stripe Charge Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from datetime import timedelta
from decimal import Decimal

from django.test.testcases import TestCase
from django.utils import timezone

from mock import patch

from djstripe.models import Charge, Customer, Invoice


FAKE_CHARGE = {
    "id": "ch_xxxxxxxxxxxx",
    "object": "charge",
    "created": 1432333679,
    "livemode": True,
    "paid": True,
    "status": "paid",
    "amount": 995,
    "currency": "usd",
    "refunded": False,
    "source": {
        "id": "card_xxxxxxxxxxxxxxx",
        "object": "card",
        "last4": "9999",
        "type": "Visa",  # type vs brand?
        "funding": "debit",
        "exp_month": 1,
        "exp_year": 2020,
        "fingerprint": "test_fingerprint",
        "country": "US",
        "name": "test_name",
        "address_line1": None,
        "address_line2": None,
        "address_city": None,
        "address_state": None,
        "address_zip": "12345",
        "address_country": None,
        "cvc_check": None,
        "address_line1_check": None,
        "address_zip_check": "pass",
        "dynamic_last4": None,
        "metadata": {},
        "customer": "cus_xxxxxxxxxxxxxxx"
    },
    "captured": True,
    "card": {
        "id": "card_xxxxxxxxxxxxxxx",
        "object": "card",
        "last4": "9999",
        "type": "Visa",  # type vs brand?
        "funding": "debit",
        "exp_month": 1,
        "exp_year": 2020,
        "fingerprint": "test_fingerprint",
        "country": "US",
        "name": "test_name",
        "address_line1": None,
        "address_line2": None,
        "address_city": None,
        "address_state": None,
        "address_zip": "12345",
        "address_country": None,
        "cvc_check": None,
        "address_line1_check": None,
        "address_zip_check": "pass",
        "dynamic_last4": None,
        "metadata": {},
        "customer": "cus_xxxxxxxxxxxxxxx"
    },
    "balance_transaction": "txn_xxxxxxxxxxxxxxx",
    "failure_message": None,
    "failure_code": None,
    "amount_refunded": 0,
    "customer": "cus_xxxxxxxxxxxxxxx",
    "invoice": "in_xxxxxxxxxxxxxxx",
    "description": "test_description",
    "dispute": None,
    "metadata": {},
    "statement_descriptor": "Basic",
    "fraud_details": {},
    "receipt_email": "test@email.com",
    "receipt_number": "0000-0000",
    "shipping": None,
    "destination": None,
    "application_fee": None,
    "fee": 0,  # Added this in... I think it moved to transaction with the new api
    "refunds": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/charges/ch_xxxxxxxxxxxx/refunds",
        "data": []
    }
}


class ChargeTest(TestCase):

    def setUp(self):
        self.customer = Customer.objects.create(stripe_id="cus_xxxxxxxxxxxxxxx")
        self.invoice = Invoice.objects.create(stripe_id="in_xxxxxxxxxxxxxxx",
                                              customer=self.customer,
                                              period_start=timezone.now(),
                                              period_end=timezone.now() + timedelta(days=5),
                                              subtotal=Decimal("35.00"),
                                              total=Decimal("50.00"),
                                              date=timezone.now(),
                                              charge="ch_xxxxxxxxxxxxxxx")

    def test_str(self):
        charge = Charge(amount=50, paid=True, stripe_id='charge_xxxxxxxxxxxxxx')
        self.assertEqual("<amount=50, paid=True, stripe_id=charge_xxxxxxxxxxxxxx>", str(charge))

    def test_sync_from_stripe_data(self):
        charge = Charge.sync_from_stripe_data(FAKE_CHARGE)

        self.assertEqual(self.invoice, charge.invoice)
        self.assertEqual("9999", charge.card_last_4)
        self.assertEqual("Visa", charge.card_kind)
        self.assertEqual(Decimal("9.95"), charge.amount)
        self.assertEqual(True, charge.paid)
        self.assertEqual(False, charge.refunded)
        self.assertEqual(True, charge.captured)
        self.assertEqual(Decimal("0"), charge.fee)
        self.assertEqual(False, charge.disputed)
        self.assertEqual("test_description", charge.description)
        self.assertEqual(None, charge.amount_refunded)

    @patch("djstripe.models.Site.objects.get_current")
    def test_send_receipt_not_sent(self, get_current_mock):
        charge = Charge(receipt_sent=True)
        charge.send_receipt()

        # Assert the condition caused exit
        self.assertFalse(get_current_mock.called)
