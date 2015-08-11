"""
.. module:: dj-stripe.tests.test_charge
   :synopsis: dj-stripe Charge Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test.testcases import TestCase
from django.utils import timezone

from mock import patch

from djstripe.models import Charge, Customer, Invoice, Account

from . import FAKE_CHARGE, FAKE_ACCOUNT


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

        with self.assertRaisesMessage(ValidationError, "A customer was not attached to this charge."):
            Charge.sync_from_stripe_data(fake_charge_copy)

    @patch("stripe.Charge.retrieve")
    @patch("stripe.Transfer.retrieve")
    @patch("djstripe.models.Account.get_default_account")
    def test_sync_from_stripe_data_with_transfer(self, default_account_mock, transfer_retrieve_mock, charge_retrieve_mock):
        default_account_mock.return_value = self.account

        fake_transfer = {
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

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"transfer": fake_transfer})

        transfer_retrieve_mock.return_value = fake_transfer
        charge_retrieve_mock.return_value = fake_charge_copy

        charge, created = Charge.get_or_create_from_stripe_object(fake_charge_copy)
        self.assertTrue(created)

        self.assertNotEqual(None, charge.transfer)
        self.assertEqual("tr_XXXXXXXXXXXX", charge.transfer.stripe_id)

    @patch("stripe.Charge.retrieve")
    @patch("stripe.Account.retrieve")
    def test_sync_from_stripe_data_with_destination(self, account_retrieve_mock, charge_retrieve_mock):
        account_retrieve_mock.return_value = FAKE_ACCOUNT

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"destination": FAKE_ACCOUNT["id"]})

        charge_retrieve_mock.return_value = fake_charge_copy

        charge, created = Charge.get_or_create_from_stripe_object(fake_charge_copy)
        self.assertTrue(created)

        self.assertEqual(2, Account.objects.count())
        account = Account.objects.get(stripe_id=FAKE_ACCOUNT["id"])

        self.assertEqual(account, charge.account)

    @patch("djstripe.models.Site.objects.get_current")
    def test_send_receipt_not_sent(self, get_current_mock):
        charge = Charge(receipt_sent=True)
        charge.send_receipt()

        # Assert the condition caused exit
        self.assertFalse(get_current_mock.called)
