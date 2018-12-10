"""
dj-stripe Charge Model Tests.
"""
from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test.testcases import TestCase

from djstripe.enums import ChargeStatus, LegacySourceType
from djstripe.models import Account, Charge, Dispute, PaymentMethod

from . import (
	FAKE_ACCOUNT, FAKE_CHARGE, FAKE_CUSTOMER, FAKE_INVOICE,
	FAKE_SUBSCRIPTION, FAKE_TRANSFER, AssertStripeFksMixin, default_account
)


class ChargeTest(AssertStripeFksMixin, TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="user", email="user@example.com"
		)
		self.customer = FAKE_CUSTOMER.create_for_user(self.user)
		self.account = default_account()

	def test_str(self):
		charge = Charge(
			amount=50,
			currency="usd",
			id="ch_test",
			status=ChargeStatus.failed,
			captured=False,
			paid=False,
		)
		self.assertEqual(str(charge), "$50.00 USD (Uncaptured)")

		charge.captured = True
		self.assertEqual(str(charge), "$50.00 USD (Failed)")
		charge.status = ChargeStatus.succeeded

		charge.dispute = Dispute()
		self.assertEqual(str(charge), "$50.00 USD (Disputed)")

		charge.dispute = None
		charge.refunded = True
		charge.amount_refunded = 50
		self.assertEqual(str(charge), "$50.00 USD (Refunded)")

		charge.refunded = False
		self.assertEqual(str(charge), "$50.00 USD (Partially refunded)")

		charge.amount_refunded = 0
		self.assertEqual(str(charge), "$50.00 USD")

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

		self.assert_fks(
			charge,
			expected_blank_fks={
				"djstripe.Account.business_logo",
				"djstripe.Charge.dispute",
				"djstripe.Charge.invoice",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.Plan.product",
			},
		)

	@patch("djstripe.models.Account.get_default_account")
	@patch("stripe.BalanceTransaction.retrieve")
	@patch("stripe.Charge.retrieve")
	@patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE))
	@patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
	def test_sync_from_stripe_data(
		self,
		subscription_retrieve_mock,
		invoice_retrieve_mock,
		charge_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
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

		self.assertEqual("card_16YKQh2eZvKYlo2Cblc5Feoo", charge.source_id)
		self.assertEqual(charge.source.type, LegacySourceType.card)

		charge_retrieve_mock.assert_not_called()
		balance_transaction_retrieve_mock.assert_not_called()

		self.assert_fks(
			charge,
			expected_blank_fks={
				"djstripe.Account.business_logo",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.Plan.product",
			},
		)

	@patch("stripe.BalanceTransaction.retrieve")
	@patch("stripe.Charge.retrieve")
	@patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE))
	@patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
	@patch("djstripe.models.Account.get_default_account")
	def test_sync_from_stripe_data_max_amount(
		self,
		default_account_mock,
		subscription_retrieve_mock,
		invoice_retrieve_mock,
		charge_retrieve_mock,
		balance_transaction_retrieve_mock,
	):
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

		charge_retrieve_mock.assert_not_called()
		balance_transaction_retrieve_mock.assert_not_called()

		self.assert_fks(
			charge,
			expected_blank_fks={
				"djstripe.Account.business_logo",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.Plan.product",
			},
		)

	@patch("djstripe.models.Account.get_default_account")
	@patch("stripe.BalanceTransaction.retrieve")
	@patch("stripe.Charge.retrieve")
	@patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
	@patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE))
	def test_sync_from_stripe_data_unsupported_source(
		self,
		invoice_retrieve_mock,
		subscription_retrieve_mock,
		charge_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		fake_charge_copy = deepcopy(FAKE_CHARGE)
		fake_charge_copy.update({"source": {"id": "test_id", "object": "unsupported"}})

		charge = Charge.sync_from_stripe_data(fake_charge_copy)
		self.assertEqual("test_id", charge.source_id)
		self.assertEqual("unsupported", charge.source.type)
		self.assertEqual(charge.source, PaymentMethod.objects.get(id="test_id"))

		charge_retrieve_mock.assert_not_called()
		balance_transaction_retrieve_mock.assert_not_called()

		self.assert_fks(
			charge,
			expected_blank_fks={
				"djstripe.Account.business_logo",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.Plan.product",
			},
		)

	@patch("djstripe.models.Account.get_default_account")
	@patch("stripe.BalanceTransaction.retrieve")
	@patch("stripe.Charge.retrieve")
	def test_sync_from_stripe_data_no_customer(
		self, charge_retrieve_mock, balance_transaction_retrieve_mock, default_account_mock
	):
		default_account_mock.return_value = self.account

		fake_charge_copy = deepcopy(FAKE_CHARGE)

		fake_charge_copy.pop("customer", None)
		# remove invoice since it requires a customer
		fake_charge_copy.pop("invoice", None)

		Charge.sync_from_stripe_data(fake_charge_copy)
		assert Charge.objects.count() == 1
		charge = Charge.objects.get()
		assert charge.customer is None

		charge_retrieve_mock.assert_not_called()
		balance_transaction_retrieve_mock.assert_not_called()

		self.assert_fks(
			charge,
			expected_blank_fks={
				"djstripe.Account.business_logo",
				"djstripe.Charge.customer",
				"djstripe.Charge.dispute",
				"djstripe.Charge.invoice",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.Plan.product",
			},
		)

	@patch("stripe.BalanceTransaction.retrieve")
	@patch("stripe.Charge.retrieve")
	@patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE))
	@patch("stripe.Transfer.retrieve")
	@patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
	@patch("djstripe.models.Account.get_default_account")
	def test_sync_from_stripe_data_with_transfer(
		self,
		default_account_mock,
		subscription_retrieve_mock,
		transfer_retrieve_mock,
		invoice_retrieve_mock,
		charge_retrieve_mock,
		balance_transaction_retrieve_mock,
	):
		default_account_mock.return_value = self.account

		fake_transfer = deepcopy(FAKE_TRANSFER)

		fake_charge_copy = deepcopy(FAKE_CHARGE)
		fake_charge_copy.update({"transfer": fake_transfer["id"]})

		transfer_retrieve_mock.return_value = fake_transfer
		charge_retrieve_mock.return_value = fake_charge_copy

		charge, created = Charge._get_or_create_from_stripe_object(
			fake_charge_copy, current_ids={fake_charge_copy["id"]}
		)
		self.assertTrue(created)

		self.assertNotEqual(None, charge.transfer)
		self.assertEqual(fake_transfer["id"], charge.transfer.id)

		charge_retrieve_mock.assert_not_called()
		balance_transaction_retrieve_mock.assert_not_called()

		self.assert_fks(
			charge,
			expected_blank_fks={
				"djstripe.Account.business_logo",
				"djstripe.Charge.dispute",
				"djstripe.Customer.coupon",
				"djstripe.Plan.product",
			},
		)

	@patch("stripe.Charge.retrieve")
	@patch("stripe.Account.retrieve")
	@patch("stripe.BalanceTransaction.retrieve")
	@patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
	@patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE))
	def test_sync_from_stripe_data_with_destination(
		self,
		invoice_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		account_retrieve_mock,
		charge_retrieve_mock,
	):
		account_retrieve_mock.return_value = FAKE_ACCOUNT

		fake_charge_copy = deepcopy(FAKE_CHARGE)
		fake_charge_copy.update({"destination": FAKE_ACCOUNT["id"]})

		charge, created = Charge._get_or_create_from_stripe_object(
			fake_charge_copy, current_ids={fake_charge_copy["id"]}
		)
		self.assertTrue(created)

		self.assertEqual(2, Account.objects.count())
		account = Account.objects.get(id=FAKE_ACCOUNT["id"])

		self.assertEqual(account, charge.account)

		charge_retrieve_mock.assert_not_called()
		balance_transaction_retrieve_mock.assert_not_called()

		self.assert_fks(
			charge,
			expected_blank_fks={
				"djstripe.Account.business_logo",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.Plan.product",
			},
		)
