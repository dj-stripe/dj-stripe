"""
.. module:: dj-stripe.tests.test_charge
   :synopsis: dj-stripe Charge Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from unittest.case import skip

from django.core.exceptions import ValidationError
from django.test.testcases import TestCase
from django.utils import timezone

from mock import patch

from djstripe.models import Charge, Customer, Invoice, Account

FAKE_CHARGE = {
    "id": "ch_16YKQi2eZvKYlo2CrCuzbJQx",
    "object": "charge",
    "created": 1439229084,
    "livemode": False,
    "paid": True,
    "status": "succeeded",
    "amount": 2200,
    "currency": "usd",
    "refunded": False,
    "source": {
        "id": "card_16YKQh2eZvKYlo2Cblc5Feoo",
        "object": "card",
        "last4": "4242",
        "brand": "Visa",
        "fingerprint": "dgs89-3jjf039jejda-0j2d",
        "funding": "credit",
        "exp_month": 2,
        "exp_year": 2016,
        "country": "US",
        "name": None,
        "address_line1": None,
        "address_line2": None,
        "address_city": None,
        "address_state": None,
        "address_zip": None,
        "address_country": None,
        "cvc_check": "pass",
        "address_line1_check": None,
        "address_zip_check": None,
        "tokenization_method": None,
        "dynamic_last4": None,
        "metadata": {},
        "customer": "cus_6lsBvm5rJ0zyHc"
    },
    "captured": True,
    "balance_transaction": "txn_16Vswu2eZvKYlo2C9DlWEgM1",
    "failure_message": None,
    "failure_code": None,
    "amount_refunded": 0,
    "customer": "cus_6lsBvm5rJ0zyHc",
    "invoice": "in_7udnik28sj829dj",
    "description": "VideoDoc consultation for ivanp0001 berkp0001",
    "dispute": None,
    "metadata": {},
    "statement_descriptor": None,
    "fraud_details": {},
    "receipt_email": None,
    "receipt_number": None,
    "shipping": None,
    "destination": None,
    "application_fee": None,
    "refunds": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/charges/ch_16YKQi2eZvKYlo2CrCuzbJQx/refunds",
        "data": []
    }
}


class ChargeTest(TestCase):

    def setUp(self):
        self.customer = Customer.objects.create(stripe_id="cus_6lsBvm5rJ0zyHc")
        self.invoice = Invoice.objects.create(stripe_id="in_7udnik28sj829dj",
                                              customer=self.customer,
                                              period_start=timezone.now(),
                                              period_end=timezone.now() + timedelta(days=5),
                                              subtotal=Decimal("35.00"),
                                              total=Decimal("50.00"),
                                              date=timezone.now(),
                                              charge="ch_16YKQi2eZvKYlo2CrCuzbJQx")
        self.account = Account.objects.create()

    def test_str(self):
        charge = Charge(amount=50, paid=True, stripe_id='charge_xxxxxxxxxxxxxx')
        self.assertEqual("<amount=50, paid=True, stripe_id=charge_xxxxxxxxxxxxxx>", str(charge))

    @patch("djstripe.models.Account.get_default_account")
    def test_sync_from_stripe_data(self, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"application_fee": {"amount": 0}})

        charge = Charge.sync_from_stripe_data(FAKE_CHARGE)

        self.assertEqual(self.invoice, charge.invoice)
        self.assertEqual(Decimal("22"), charge.amount)
        self.assertEqual(True, charge.paid)
        self.assertEqual(False, charge.refunded)
        self.assertEqual(True, charge.captured)
        self.assertEqual(False, charge.disputed)
        self.assertEqual("VideoDoc consultation for ivanp0001 berkp0001", charge.description)
        self.assertEqual(0, charge.amount_refunded)

        self.assertEqual("card_16YKQh2eZvKYlo2Cblc5Feoo", charge.source_stripe_id)
        self.assertEqual("card", charge.source_type)

        self.assertEqual("4242", charge.card_last_4)
        self.assertEqual("Visa", charge.card_kind)

    @patch("djstripe.models.Account.get_default_account")
    def test_sync_from_stripe_data_unsupported_source(self, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"source": {"id": "test_id", "object": "unsupported"}})

        charge = Charge.sync_from_stripe_data(fake_charge_copy)
        self.assertEqual("test_id", charge.source_stripe_id)
        self.assertEqual("unsupported", charge.source_type)
        self.assertEqual(None, charge.card)

    @patch("djstripe.models.Account.get_default_account")
    def test_sync_from_stripe_data_no_customer(self, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.pop("customer", None)

        with self.assertRaises(ValidationError):
            Charge.sync_from_stripe_data(fake_charge_copy)

    @skip
    @patch("djstripe.models.Account.get_default_account")
    def test_sync_from_stripe_data_with_transfer(self, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({
            "transfer": {
                "amount": 455,
                "currency": "usd",
                "date": 1348876800,
                "description": None,
                "id": "tr_XXXXXXXXXXXX",
                "livemode": True,
                "object": "transfer",
                "other_transfers": [],
                "status": "paid",
                "summary": {
                    "adjustment_count": 0,
                    "adjustment_fee_details": [],
                    "adjustment_fees": 0,
                    "adjustment_gross": 0,
                    "charge_count": 1,
                    "charge_fee_details": [{
                        "amount": 45,
                        "application": None,
                        "currency": "usd",
                        "description": None,
                        "type": "stripe_fee"
                    }],
                    "charge_fees": 45,
                    "charge_gross": 500,
                    "collected_fee_count": 0,
                    "collected_fee_gross": 0,
                    "currency": "usd",
                    "net": 455,
                    "refund_count": 0,
                    "refund_fees": 0,
                    "refund_gross": 0,
                    "validation_count": 0,
                    "validation_fees": 0
                }
            }
        })

        print(fake_charge_copy)

        charge = Charge.sync_from_stripe_data(fake_charge_copy)

        self.assertNotEqual(None, charge.transfer)
        self.assertEqual("tr_XXXXXXXXXXXX", charge.transfer.id)

    @skip
    def test_sync_from_stripe_data_with_destination(self):
        account_stripe_id = "acct_xxxxxxxxxxxxxxx"

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"destination": account_stripe_id})

        charge = Charge.sync_from_stripe_data(fake_charge_copy)

        self.assertEqual(2, Account.objects.count())
        print(Account.objects.all())
        account = Account.objects.get(stripe_id=account_stripe_id)

        self.assertEqual(account, charge.account)

    @patch("djstripe.models.Site.objects.get_current")
    def test_send_receipt_not_sent(self, get_current_mock):
        charge = Charge(receipt_sent=True)
        charge.send_receipt()

        # Assert the condition caused exit
        self.assertFalse(get_current_mock.called)
