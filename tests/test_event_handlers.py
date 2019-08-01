"""
dj-stripe Event Handler tests
"""
import decimal
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe.models import (
	Card, Charge, Coupon, Customer, Dispute, DjstripePaymentMethod,
	Event, Invoice, InvoiceItem, Plan, Subscription, Transfer
)

from . import (
	FAKE_BALANCE_TRANSACTION, FAKE_CARD, FAKE_CHARGE, FAKE_CHARGE_II, FAKE_COUPON,
	FAKE_CUSTOMER, FAKE_CUSTOMER_II, FAKE_DISPUTE,
	FAKE_EVENT_ACCOUNT_APPLICATION_DEAUTHORIZED, FAKE_EVENT_CHARGE_SUCCEEDED,
	FAKE_EVENT_CUSTOMER_CREATED, FAKE_EVENT_CUSTOMER_DELETED,
	FAKE_EVENT_CUSTOMER_DISCOUNT_CREATED, FAKE_EVENT_CUSTOMER_DISCOUNT_DELETED,
	FAKE_EVENT_CUSTOMER_SOURCE_CREATED, FAKE_EVENT_CUSTOMER_SOURCE_DELETED,
	FAKE_EVENT_CUSTOMER_SOURCE_DELETED_DUPE, FAKE_EVENT_CUSTOMER_SUBSCRIPTION_CREATED,
	FAKE_EVENT_CUSTOMER_SUBSCRIPTION_DELETED, FAKE_EVENT_DISPUTE_CREATED,
	FAKE_EVENT_INVOICE_CREATED, FAKE_EVENT_INVOICE_DELETED, FAKE_EVENT_INVOICE_UPCOMING,
	FAKE_EVENT_INVOICEITEM_CREATED, FAKE_EVENT_INVOICEITEM_DELETED,
	FAKE_EVENT_PLAN_CREATED, FAKE_EVENT_PLAN_DELETED, FAKE_EVENT_PLAN_REQUEST_IS_OBJECT,
	FAKE_EVENT_TRANSFER_CREATED, FAKE_EVENT_TRANSFER_DELETED, FAKE_INVOICE,
	FAKE_INVOICE_II, FAKE_INVOICEITEM, FAKE_PAYMENT_INTENT_I, FAKE_PLAN, FAKE_PRODUCT,
	FAKE_SUBSCRIPTION, FAKE_SUBSCRIPTION_III, FAKE_TRANSFER,
	IS_STATICMETHOD_AUTOSPEC_SUPPORTED, default_account
)


class EventTestCase(TestCase):
	#
	# Helpers
	#

	@patch("stripe.Event.retrieve", autospec=True)
	def _create_event(self, event_data, event_retrieve_mock, patch_data=None):
		event_data = deepcopy(event_data)

		if patch_data:
			event_data.update(patch_data)

		event_retrieve_mock.return_value = event_data
		event = Event.sync_from_stripe_data(event_data)

		return event


class TestAccountEvents(EventTestCase):
	@patch("stripe.Event.retrieve", autospec=True)
	def test_account_deauthorized_event(self, event_retrieve_mock):
		fake_stripe_event = deepcopy(FAKE_EVENT_ACCOUNT_APPLICATION_DEAUTHORIZED)

		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()


class TestChargeEvents(EventTestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="pydanny", email="pydanny@gmail.com"
		)

	@patch(
		"djstripe.models.Account.get_default_account",
		autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
	)
	@patch(
		"stripe.BalanceTransaction.retrieve", return_value=deepcopy(FAKE_BALANCE_TRANSACTION)
	)
	@patch("stripe.Charge.retrieve", autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Event.retrieve", autospec=True)
	@patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	@patch(
		"stripe.Subscription.retrieve",
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	def test_charge_created(
		self,
		subscription_retrieve_mock,
		product_retrieve_mock,
		invoice_retrieve_mock,
		event_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		balance_transaction_retrieve_mock,
		account_mock,
	):
		FAKE_CUSTOMER.create_for_user(self.user)
		fake_stripe_event = deepcopy(FAKE_EVENT_CHARGE_SUCCEEDED)
		event_retrieve_mock.return_value = fake_stripe_event
		charge_retrieve_mock.return_value = fake_stripe_event["data"]["object"]
		account_mock.return_value = default_account()

		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()

		charge = Charge.objects.get(id=fake_stripe_event["data"]["object"]["id"])
		self.assertEqual(
			charge.amount, fake_stripe_event["data"]["object"]["amount"] / decimal.Decimal("100")
		)
		self.assertEqual(charge.status, fake_stripe_event["data"]["object"]["status"])


class TestCustomerEvents(EventTestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="pydanny", email="pydanny@gmail.com"
		)
		self.customer = FAKE_CUSTOMER.create_for_user(self.user)

	@patch("stripe.Customer.retrieve", return_value=FAKE_CUSTOMER, autospec=True)
	@patch("stripe.Event.retrieve", autospec=True)
	def test_customer_created(self, event_retrieve_mock, customer_retrieve_mock):
		fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_CREATED)
		event_retrieve_mock.return_value = fake_stripe_event

		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()

		customer = Customer.objects.get(id=fake_stripe_event["data"]["object"]["id"])
		self.assertEqual(customer.balance, fake_stripe_event["data"]["object"]["balance"])
		self.assertEqual(customer.currency, fake_stripe_event["data"]["object"]["currency"])

	@patch("stripe.Customer.retrieve", return_value=FAKE_CUSTOMER, autospec=True)
	def test_customer_deleted(self, customer_retrieve_mock):
		FAKE_CUSTOMER.create_for_user(self.user)
		event = self._create_event(FAKE_EVENT_CUSTOMER_CREATED)
		event.invoke_webhook_handlers()

		event = self._create_event(FAKE_EVENT_CUSTOMER_DELETED)
		event.invoke_webhook_handlers()
		customer = Customer.objects.get(id=FAKE_CUSTOMER["id"])
		self.assertIsNotNone(customer.date_purged)

	@patch("stripe.Coupon.retrieve", return_value=FAKE_COUPON, autospec=True)
	@patch(
		"stripe.Event.retrieve",
		return_value=FAKE_EVENT_CUSTOMER_DISCOUNT_CREATED,
		autospec=True,
	)
	def test_customer_discount_created(self, event_retrieve_mock, coupon_retrieve_mock):
		fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_DISCOUNT_CREATED)
		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()

		self.assertIsNotNone(event.customer)
		self.assertEqual(event.customer.id, FAKE_CUSTOMER["id"])
		self.assertIsNotNone(event.customer.coupon)

	@patch("stripe.Coupon.retrieve", return_value=FAKE_COUPON, autospec=True)
	@patch(
		"stripe.Event.retrieve",
		return_value=FAKE_EVENT_CUSTOMER_DISCOUNT_DELETED,
		autospec=True,
	)
	def test_customer_discount_deleted(self, event_retrieve_mock, coupon_retrieve_mock):
		coupon = Coupon.sync_from_stripe_data(FAKE_COUPON)
		self.customer.coupon = coupon

		fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_DISCOUNT_DELETED)
		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()

		self.assertIsNotNone(event.customer)
		self.assertEqual(event.customer.id, FAKE_CUSTOMER["id"])
		self.assertIsNone(event.customer.coupon)

	@patch("stripe.Customer.retrieve", return_value=FAKE_CUSTOMER, autospec=True)
	@patch("stripe.Event.retrieve", autospec=True)
	def test_customer_card_created(self, event_retrieve_mock, customer_retrieve_mock):
		fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_SOURCE_CREATED)
		event_retrieve_mock.return_value = fake_stripe_event

		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()

		card = Card.objects.get(id=fake_stripe_event["data"]["object"]["id"])
		self.assertIn(card, self.customer.legacy_cards.all())
		self.assertEqual(card.brand, fake_stripe_event["data"]["object"]["brand"])
		self.assertEqual(card.last4, fake_stripe_event["data"]["object"]["last4"])

	@patch("stripe.Event.retrieve", autospec=True)
	def test_customer_unknown_source_created(self, event_retrieve_mock):
		fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_SOURCE_CREATED)
		fake_stripe_event["data"]["object"]["object"] = "unknown"
		fake_stripe_event["data"]["object"][
			"id"
		] = "card_xxx_test_customer_unk_source_created"
		event_retrieve_mock.return_value = fake_stripe_event

		FAKE_CUSTOMER.create_for_user(self.user)

		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()

		self.assertFalse(
			Card.objects.filter(id=fake_stripe_event["data"]["object"]["id"]).exists()
		)

	def test_customer_default_source_deleted(self):
		self.customer.default_source = DjstripePaymentMethod.objects.get(id=FAKE_CARD["id"])
		self.customer.save()
		self.assertIsNotNone(self.customer.default_source)
		self.assertTrue(self.customer.has_valid_source())

		event = self._create_event(FAKE_EVENT_CUSTOMER_SOURCE_DELETED)
		event.invoke_webhook_handlers()

		customer = Customer.objects.get(id=FAKE_CUSTOMER["id"])
		self.assertIsNone(customer.default_source)
		self.assertFalse(customer.has_valid_source())

	def test_customer_source_double_delete(self):
		event = self._create_event(FAKE_EVENT_CUSTOMER_SOURCE_DELETED)
		event.invoke_webhook_handlers()

		event = self._create_event(FAKE_EVENT_CUSTOMER_SOURCE_DELETED_DUPE)
		event.invoke_webhook_handlers()

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
	@patch(
		"stripe.Subscription.retrieve",
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	@patch("stripe.Event.retrieve", autospec=True)
	def test_customer_subscription_created(
		self,
		event_retrieve_mock,
		product_retrieve_mock,
		subscription_retrieve_mock,
		plan_retrieve_mock,
	):
		fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_SUBSCRIPTION_CREATED)
		event_retrieve_mock.return_value = fake_stripe_event

		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()

		subscription = Subscription.objects.get(id=fake_stripe_event["data"]["object"]["id"])
		self.assertIn(subscription, self.customer.subscriptions.all())
		self.assertEqual(subscription.status, fake_stripe_event["data"]["object"]["status"])
		self.assertEqual(
			subscription.quantity, fake_stripe_event["data"]["object"]["quantity"]
		)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
	@patch(
		"stripe.Subscription.retrieve",
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True)
	def test_customer_subscription_deleted(
		self,
		customer_retrieve_mock,
		product_retrieve_mock,
		subscription_retrieve_mock,
		plan_retrieve_mock,
	):
		event = self._create_event(FAKE_EVENT_CUSTOMER_SUBSCRIPTION_CREATED)
		event.invoke_webhook_handlers()

		Subscription.objects.get(id=FAKE_SUBSCRIPTION["id"])

		event = self._create_event(FAKE_EVENT_CUSTOMER_SUBSCRIPTION_DELETED)
		event.invoke_webhook_handlers()

		with self.assertRaises(Subscription.DoesNotExist):
			Subscription.objects.get(id=FAKE_SUBSCRIPTION["id"])

	@patch("stripe.Customer.retrieve", autospec=True)
	@patch("stripe.Event.retrieve", autospec=True)
	def test_customer_bogus_event_type(self, event_retrieve_mock, customer_retrieve_mock):
		fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_CREATED)
		fake_stripe_event["data"]["object"]["customer"] = fake_stripe_event["data"][
			"object"
		]["id"]
		fake_stripe_event["type"] = "customer.praised"

		event_retrieve_mock.return_value = fake_stripe_event
		customer_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()


class TestDisputeEvents(EventTestCase):
	@patch("stripe.Dispute.retrieve", return_value=deepcopy(FAKE_DISPUTE), autospec=True)
	@patch(
		"stripe.Event.retrieve",
		return_value=deepcopy(FAKE_EVENT_DISPUTE_CREATED),
		autospec=True,
	)
	def test_dispute_created(self, event_retrieve_mock, dispute_retrieve_mock):
		fake_stripe_event = deepcopy(FAKE_EVENT_DISPUTE_CREATED)
		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()
		dispute = Dispute.objects.get()
		self.assertEqual(dispute.id, FAKE_DISPUTE["id"])


class TestInvoiceEvents(EventTestCase):
	@patch(
		"djstripe.models.Account.get_default_account",
		autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
	)
	@patch(
		"stripe.BalanceTransaction.retrieve",
		return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
		autospec=True,
	)
	@patch(
		"stripe.Subscription.retrieve",
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True)
	@patch("stripe.Event.retrieve", autospec=True)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_invoice_created_no_existing_customer(
		self,
		product_retrieve_mock,
		event_retrieve_mock,
		invoice_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		customer_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = default_account()

		fake_stripe_event = deepcopy(FAKE_EVENT_INVOICE_CREATED)
		event_retrieve_mock.return_value = fake_stripe_event

		invoice_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()

		self.assertEqual(Customer.objects.count(), 1)
		customer = Customer.objects.get()
		self.assertEqual(customer.subscriber, None)

	@patch(
		"djstripe.models.Account.get_default_account",
		autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
	)
	@patch(
		"stripe.BalanceTransaction.retrieve",
		return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
		autospec=True,
	)
	@patch(
		"stripe.Subscription.retrieve",
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Invoice.retrieve", autospec=True)
	@patch("stripe.Event.retrieve", autospec=True)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_invoice_created(
		self,
		product_retrieve_mock,
		event_retrieve_mock,
		invoice_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		customer_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = default_account()

		user = get_user_model().objects.create_user(
			username="pydanny", email="pydanny@gmail.com"
		)
		FAKE_CUSTOMER.create_for_user(user)

		fake_stripe_event = deepcopy(FAKE_EVENT_INVOICE_CREATED)
		event_retrieve_mock.return_value = fake_stripe_event

		invoice_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()

		invoice = Invoice.objects.get(id=fake_stripe_event["data"]["object"]["id"])
		self.assertEqual(
			invoice.amount_due,
			fake_stripe_event["data"]["object"]["amount_due"] / decimal.Decimal("100"),
		)
		self.assertEqual(invoice.paid, fake_stripe_event["data"]["object"]["paid"])

	@patch(
		"djstripe.models.Account.get_default_account",
		autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
	)
	@patch(
		"stripe.BalanceTransaction.retrieve",
		return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
		autospec=True,
	)
	@patch(
		"stripe.Subscription.retrieve",
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_invoice_deleted(
		self,
		product_retrieve_mock,
		invoice_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = default_account()

		user = get_user_model().objects.create_user(
			username="pydanny", email="pydanny@gmail.com"
		)
		FAKE_CUSTOMER.create_for_user(user)

		event = self._create_event(FAKE_EVENT_INVOICE_CREATED)
		event.invoke_webhook_handlers()

		Invoice.objects.get(id=FAKE_INVOICE["id"])

		event = self._create_event(FAKE_EVENT_INVOICE_DELETED)
		event.invoke_webhook_handlers()

		with self.assertRaises(Invoice.DoesNotExist):
			Invoice.objects.get(id=FAKE_INVOICE["id"])

	def test_invoice_upcoming(self):
		# Ensure that invoice upcoming events are processed - No actual
		# process occurs so the operation is an effective no-op.
		event = self._create_event(FAKE_EVENT_INVOICE_UPCOMING)
		event.invoke_webhook_handlers()


class TestInvoiceItemEvents(EventTestCase):
	@patch(
		"djstripe.models.Account.get_default_account",
		autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
	)
	@patch(
		"stripe.BalanceTransaction.retrieve",
		return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
		autospec=True,
	)
	@patch(
		"stripe.Subscription.retrieve",
		return_value=deepcopy(FAKE_SUBSCRIPTION_III),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II), autospec=True)
	@patch(
		"stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II), autospec=True
	)
	@patch("stripe.InvoiceItem.retrieve", autospec=True)
	@patch("stripe.Event.retrieve", autospec=True)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_invoiceitem_created(
		self,
		product_retrieve_mock,
		event_retrieve_mock,
		invoiceitem_retrieve_mock,
		invoice_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = default_account()

		user = get_user_model().objects.create_user(
			username="pydanny", email="pydanny@gmail.com"
		)
		FAKE_CUSTOMER_II.create_for_user(user)

		fake_stripe_event = deepcopy(FAKE_EVENT_INVOICEITEM_CREATED)
		event_retrieve_mock.return_value = fake_stripe_event

		invoiceitem_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()

		invoiceitem = InvoiceItem.objects.get(id=fake_stripe_event["data"]["object"]["id"])
		self.assertEqual(
			invoiceitem.amount,
			fake_stripe_event["data"]["object"]["amount"] / decimal.Decimal("100"),
		)

	@patch(
		"djstripe.models.Account.get_default_account",
		autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
	)
	@patch(
		"stripe.BalanceTransaction.retrieve",
		return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
		autospec=True,
	)
	@patch(
		"stripe.Subscription.retrieve",
		return_value=deepcopy(FAKE_SUBSCRIPTION_III),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II), autospec=True)
	@patch(
		"stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II), autospec=True
	)
	@patch(
		"stripe.InvoiceItem.retrieve", return_value=deepcopy(FAKE_INVOICEITEM), autospec=True
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_invoiceitem_deleted(
		self,
		product_retrieve_mock,
		invoiceitem_retrieve_mock,
		invoice_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = default_account()

		user = get_user_model().objects.create_user(
			username="pydanny", email="pydanny@gmail.com"
		)
		FAKE_CUSTOMER_II.create_for_user(user)

		event = self._create_event(FAKE_EVENT_INVOICEITEM_CREATED)
		event.invoke_webhook_handlers()

		InvoiceItem.objects.get(id=FAKE_INVOICEITEM["id"])

		event = self._create_event(FAKE_EVENT_INVOICEITEM_DELETED)
		event.invoke_webhook_handlers()

		with self.assertRaises(InvoiceItem.DoesNotExist):
			InvoiceItem.objects.get(id=FAKE_INVOICEITEM["id"])


class TestPlanEvents(EventTestCase):
	@patch("stripe.Plan.retrieve", autospec=True)
	@patch("stripe.Event.retrieve", autospec=True)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_plan_created(
		self, product_retrieve_mock, event_retrieve_mock, plan_retrieve_mock
	):
		fake_stripe_event = deepcopy(FAKE_EVENT_PLAN_CREATED)
		event_retrieve_mock.return_value = fake_stripe_event
		plan_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()

		plan = Plan.objects.get(id=fake_stripe_event["data"]["object"]["id"])
		self.assertEqual(plan.nickname, fake_stripe_event["data"]["object"]["nickname"])

	@patch("stripe.Plan.retrieve", return_value=FAKE_PLAN, autospec=True)
	@patch(
		"stripe.Event.retrieve", return_value=FAKE_EVENT_PLAN_REQUEST_IS_OBJECT, autospec=True
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_plan_updated_request_object(
		self, product_retrieve_mock, event_retrieve_mock, plan_retrieve_mock
	):
		plan_retrieve_mock.return_value = FAKE_EVENT_PLAN_REQUEST_IS_OBJECT["data"]["object"]

		event = Event.sync_from_stripe_data(FAKE_EVENT_PLAN_REQUEST_IS_OBJECT)
		event.invoke_webhook_handlers()

		plan = Plan.objects.get(id=FAKE_EVENT_PLAN_REQUEST_IS_OBJECT["data"]["object"]["id"])
		self.assertEqual(
			plan.nickname, FAKE_EVENT_PLAN_REQUEST_IS_OBJECT["data"]["object"]["nickname"]
		)

	@patch("stripe.Plan.retrieve", return_value=FAKE_PLAN, autospec=True)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_plan_deleted(self, product_retrieve_mock, plan_retrieve_mock):

		event = self._create_event(FAKE_EVENT_PLAN_CREATED)
		event.invoke_webhook_handlers()

		Plan.objects.get(id=FAKE_PLAN["id"])

		event = self._create_event(FAKE_EVENT_PLAN_DELETED)
		event.invoke_webhook_handlers()

		with self.assertRaises(Plan.DoesNotExist):
			Plan.objects.get(id=FAKE_PLAN["id"])


class TestTransferEvents(EventTestCase):
	@patch("stripe.Transfer.retrieve", autospec=True)
	@patch("stripe.Event.retrieve", autospec=True)
	def test_transfer_created(self, event_retrieve_mock, transfer_retrieve_mock):
		fake_stripe_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
		event_retrieve_mock.return_value = fake_stripe_event
		transfer_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

		event = Event.sync_from_stripe_data(fake_stripe_event)
		event.invoke_webhook_handlers()

		transfer = Transfer.objects.get(id=fake_stripe_event["data"]["object"]["id"])
		self.assertEqual(
			transfer.amount,
			fake_stripe_event["data"]["object"]["amount"] / decimal.Decimal("100"),
		)

	@patch("stripe.Transfer.retrieve", return_value=FAKE_TRANSFER, autospec=True)
	def test_transfer_deleted(self, transfer_retrieve_mock):
		event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)
		event.invoke_webhook_handlers()

		Transfer.objects.get(id=FAKE_TRANSFER["id"])

		event = self._create_event(FAKE_EVENT_TRANSFER_DELETED)
		event.invoke_webhook_handlers()

		with self.assertRaises(Transfer.DoesNotExist):
			Transfer.objects.get(id=FAKE_TRANSFER["id"])

		event = self._create_event(FAKE_EVENT_TRANSFER_DELETED)
		event.invoke_webhook_handlers()
