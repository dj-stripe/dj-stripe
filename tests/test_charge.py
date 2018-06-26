"""
.. module:: dj-stripe.tests.test_charge
   :synopsis: dj-stripe Charge Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from copy import deepcopy
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test.testcases import TestCase
from mock import patch
from six import text_type

from djstripe.enums import ChargeStatus, LegacySourceType
from djstripe.models import Account, Charge, Dispute, PaymentMethod

from . import FAKE_ACCOUNT, FAKE_CHARGE, FAKE_CUSTOMER, FAKE_TRANSFER, default_account


class ChargeTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="user", email="user@example.com")
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)
        self.account = default_account()

    def test_str(self):
        charge = Charge(
            amount=50, currency="usd", stripe_id="ch_test",
            status=ChargeStatus.failed,
            captured=False,
            paid=False,
        )
        self.assertEqual(text_type(charge), "$50.00 USD (Uncaptured)")

        charge.captured = True
        self.assertEqual(text_type(charge), "$50.00 USD (Failed)")
        charge.status = ChargeStatus.succeeded

        charge.dispute = Dispute()
        self.assertEqual(text_type(charge), "$50.00 USD (Disputed)")

        charge.dispute = None
        charge.refunded = True
        charge.amount_refunded = 50
        self.assertEqual(text_type(charge), "$50.00 USD (Refunded)")

        charge.refunded = False
        self.assertEqual(text_type(charge), "$50.00 USD (Partially refunded)")

        charge.amount_refunded = 0
        self.assertEqual(text_type(charge), "$50.00 USD")

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    def test_capture_charge(self, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_no_invoice = deepcopy(FAKE_CHARGE)
        fake_charge_no_invoice.update({"invoice": None})

        charge_retrieve_mock.return_value = fake_charge_no_invoice

        charge, created = Charge._get_or_create_from_stripe_object(fake_charge_no_invoice)
        self.assertTrue(created)

        captured_charge = charge.capture()
        self.assertTrue(captured_charge.captured)

    @patch("djstripe.models.Account.get_default_account")
    def test_sync_from_stripe_data(self, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"application_fee": {"amount": 0}})

        charge = Charge.sync_from_stripe_data(FAKE_CHARGE)

        self.assertEqual(Decimal("22"), charge.amount)
        self.assertEqual(True, charge.paid)
        self.assertEqual(False, charge.refunded)
        self.assertEqual(True, charge.captured)
        self.assertEqual(False, charge.disputed)
        self.assertEqual("VideoDoc consultation for ivanp0001 berkp0001", charge.description)
        self.assertEqual(0, charge.amount_refunded)

        self.assertEqual("card_16YKQh2eZvKYlo2Cblc5Feoo", charge.source_stripe_id)
        self.assertEqual(charge.source_type, LegacySourceType.card)

    @patch("djstripe.models.Account.get_default_account")
    def test_sync_from_stripe_data_max_amount(self, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        # https://support.stripe.com/questions/what-is-the-maximum-amount-i-can-charge-with-stripe
        fake_charge_copy.update({"amount": 99999999})

        charge = Charge.sync_from_stripe_data(fake_charge_copy)

        self.assertEqual(Decimal("999999.99"), charge.amount)
        self.assertEqual(True, charge.paid)
        self.assertEqual(False, charge.refunded)
        self.assertEqual(True, charge.captured)
        self.assertEqual(False, charge.disputed)
        self.assertEqual(0, charge.amount_refunded)

    @patch("djstripe.models.Account.get_default_account")
    def test_sync_from_stripe_data_unsupported_source(self, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"source": {"id": "test_id", "object": "unsupported"}})

        charge = Charge.sync_from_stripe_data(fake_charge_copy)
        self.assertEqual("test_id", charge.source_stripe_id)
        self.assertEqual("unsupported", charge.source_type)
        self.assertEqual(charge.source, PaymentMethod.objects.get(id="test_id"))

    @patch("djstripe.models.Account.get_default_account")
    def test_sync_from_stripe_data_no_customer(self, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.pop("customer", None)

        Charge.sync_from_stripe_data(fake_charge_copy)
        assert Charge.objects.count() == 1
        charge = Charge.objects.get()
        assert charge.customer is None

    @patch("stripe.Charge.retrieve")
    @patch("stripe.Transfer.retrieve")
    @patch("djstripe.models.Account.get_default_account")
    def test_sync_from_stripe_data_with_transfer(self, default_account_mock, transfer_retrieve_mock,
                                                 charge_retrieve_mock):
        default_account_mock.return_value = self.account

        fake_transfer = deepcopy(FAKE_TRANSFER)

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"transfer": fake_transfer["id"]})

        transfer_retrieve_mock.return_value = fake_transfer
        charge_retrieve_mock.return_value = fake_charge_copy

        charge, created = Charge._get_or_create_from_stripe_object(fake_charge_copy)
        self.assertTrue(created)

        self.assertNotEqual(None, charge.transfer)
        self.assertEqual(fake_transfer["id"], charge.transfer.stripe_id)

    @patch("stripe.Charge.retrieve")
    @patch("stripe.Account.retrieve")
    def test_sync_from_stripe_data_with_destination(self, account_retrieve_mock, charge_retrieve_mock):
        account_retrieve_mock.return_value = FAKE_ACCOUNT

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"destination": FAKE_ACCOUNT["id"]})

        charge_retrieve_mock.return_value = fake_charge_copy

        charge, created = Charge._get_or_create_from_stripe_object(fake_charge_copy)
        self.assertTrue(created)

        self.assertEqual(2, Account.objects.count())
        account = Account.objects.get(stripe_id=FAKE_ACCOUNT["id"])

        self.assertEqual(account, charge.account)
