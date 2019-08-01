"""
dj-stripe Invoice Model Tests.
"""
from copy import deepcopy
from unittest.mock import ANY, patch

from django.contrib.auth import get_user_model
from django.test.testcases import TestCase
from stripe.error import InvalidRequestError

from djstripe.models import Invoice, Plan, Subscription, UpcomingInvoice
from djstripe.settings import STRIPE_SECRET_KEY

from . import (
	FAKE_BALANCE_TRANSACTION, FAKE_CHARGE, FAKE_CUSTOMER, FAKE_INVOICE,
	FAKE_INVOICEITEM_II, FAKE_PAYMENT_INTENT_I, FAKE_PLAN, FAKE_PRODUCT,
	FAKE_SUBSCRIPTION, FAKE_UPCOMING_INVOICE, IS_ASSERT_CALLED_AUTOSPEC_SUPPORTED,
	IS_STATICMETHOD_AUTOSPEC_SUPPORTED, AssertStripeFksMixin, default_account
)


class InvoiceTest(AssertStripeFksMixin, TestCase):
	def setUp(self):
		self.account = default_account()
		self.user = get_user_model().objects.create_user(
			username="pydanny", email="pydanny@gmail.com"
		)
		self.customer = FAKE_CUSTOMER.create_for_user(self.user)

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
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_sync_from_stripe_data(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account
		invoice = Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))
		self.assertEqual(
			invoice.get_stripe_dashboard_url(), self.customer.get_stripe_dashboard_url()
		)
		self.assertEqual(str(invoice), "Invoice #{}".format(FAKE_INVOICE["number"]))
		self.assertGreater(len(invoice.status_transitions.keys()), 1)
		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Subscription.pending_setup_intent",
			},
		)

	@patch("stripe.Invoice.retrieve", autospec=True)
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
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_retry_true(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
		invoice_retrieve_mock,
	):
		default_account_mock.return_value = self.account

		fake_invoice = deepcopy(FAKE_INVOICE)
		fake_invoice.update({"paid": False, "closed": False})
		invoice_retrieve_mock.return_value = fake_invoice

		invoice = Invoice.sync_from_stripe_data(fake_invoice)
		return_value = invoice.retry()

		invoice_retrieve_mock.assert_called_once_with(
			id=invoice.id, api_key=STRIPE_SECRET_KEY, expand=[]
		)
		self.assertTrue(return_value)

		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Subscription.pending_setup_intent",
			},
		)

	@patch("stripe.Invoice.retrieve", autospec=True)
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
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_retry_false(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
		invoice_retrieve_mock,
	):
		default_account_mock.return_value = self.account

		fake_invoice = deepcopy(FAKE_INVOICE)
		invoice_retrieve_mock.return_value = fake_invoice

		invoice = Invoice.sync_from_stripe_data(fake_invoice)
		return_value = invoice.retry()

		self.assertFalse(invoice_retrieve_mock.called)
		self.assertFalse(return_value)

		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Subscription.pending_setup_intent",
			},
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
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_status_paid(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoice = Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

		self.assertEqual(Invoice.STATUS_PAID, invoice.status)

		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Subscription.pending_setup_intent",
			},
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
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_status_open(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice_data.update({"paid": False, "closed": False})
		invoice = Invoice.sync_from_stripe_data(invoice_data)

		self.assertEqual(Invoice.STATUS_OPEN, invoice.status)

		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Subscription.pending_setup_intent",
			},
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
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_status_forgiven(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice_data.update({"paid": False, "closed": False, "forgiven": True})
		invoice = Invoice.sync_from_stripe_data(invoice_data)

		self.assertEqual(Invoice.STATUS_FORGIVEN, invoice.status)

		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Subscription.pending_setup_intent",
			},
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
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_status_forgiven_deprecated(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		# forgiven parameter deprecated in API 2018-11-08 - see https://stripe.com/docs/upgrades#2018-11-08
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice_data.update({"paid": False, "closed": False})
		invoice_data.pop("forgiven", None)  # TODO remove
		invoice_data["status"] = "uncollectible"
		invoice = Invoice.sync_from_stripe_data(invoice_data)

		self.assertEqual(Invoice.STATUS_FORGIVEN, invoice.status)

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
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_status_forgiven_default(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		# forgiven parameter deprecated in API 2018-11-08 - see https://stripe.com/docs/upgrades#2018-11-08
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice_data.update({"paid": False, "closed": False})
		invoice_data.pop("forgiven", None)  # TODO remove
		invoice = Invoice.sync_from_stripe_data(invoice_data)

		self.assertEqual(Invoice.STATUS_OPEN, invoice.status)

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
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_status_closed(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice_data.update({"paid": False})
		invoice = Invoice.sync_from_stripe_data(invoice_data)

		self.assertEqual(Invoice.STATUS_CLOSED, invoice.status)

		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Subscription.pending_setup_intent",
			},
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
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_status_closed_deprecated(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		# closed parameter deprecated in API 2018-11-08 - see https://stripe.com/docs/upgrades#2018-11-08
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice_data.update({"paid": False})
		invoice_data["auto_advance"] = False

		invoice = Invoice.sync_from_stripe_data(invoice_data)

		self.assertEqual(Invoice.STATUS_CLOSED, invoice.status)
		self.assertEqual(invoice.auto_advance, invoice_data["auto_advance"])

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
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_status_closed_default(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		# closed parameter deprecated in API 2018-11-08 - see https://stripe.com/docs/upgrades#2018-11-08
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice_data.update({"paid": False})
		invoice_data.pop("auto_advance")
		invoice_data.pop("closed", None)  # TODO remove
		invoice_data.pop("status")

		invoice = Invoice.sync_from_stripe_data(invoice_data)

		self.assertEqual(Invoice.STATUS_OPEN, invoice.status)

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
		"stripe.Plan.retrieve",
		return_value=deepcopy(FAKE_PLAN),
		autospec=IS_ASSERT_CALLED_AUTOSPEC_SUPPORTED,
	)
	@patch("stripe.Subscription.retrieve", autospec=IS_ASSERT_CALLED_AUTOSPEC_SUPPORTED)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_sync_no_subscription(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		plan_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice_data.update({"subscription": None})
		invoice_data["lines"]["data"][0]["subscription"] = None
		invoice = Invoice.sync_from_stripe_data(invoice_data)

		self.assertEqual(None, invoice.subscription)

		self.assertEqual(FAKE_CHARGE["id"], invoice.charge.id)
		self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

		# charge_retrieve_mock.assert_not_called()
		plan_retrieve_mock.assert_not_called()
		subscription_retrieve_mock.assert_not_called()

		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.Invoice.subscription",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Subscription.pending_setup_intent",
			},
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
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_invoice_with_subscription_invoice_items(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice = Invoice.sync_from_stripe_data(invoice_data)

		items = invoice.invoiceitems.all()
		self.assertEqual(1, len(items))

		# Previously the test asserted item_id="{invoice_id}-{subscription_id}",
		# but this doesn't match what I'm seeing from Stripe
		# I'm not sure if it's possible to predict the whole item id now, sli seems to not reference anything
		item_id_prefix = "{invoice_id}-sli_".format(invoice_id=invoice.id)
		self.assertTrue(items[0].id.startswith(item_id_prefix))
		self.assertEqual(items[0].subscription.id, FAKE_SUBSCRIPTION["id"])

		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Subscription.pending_setup_intent",
			},
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
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_invoice_with_no_invoice_items(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice_data["lines"] = []
		invoice = Invoice.sync_from_stripe_data(invoice_data)

		self.assertIsNotNone(invoice.plan)  # retrieved from invoice item
		self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Subscription.pending_setup_intent",
			},
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
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_invoice_with_non_subscription_invoice_items(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice_data["lines"]["data"].append(deepcopy(FAKE_INVOICEITEM_II))
		invoice_data["lines"]["total_count"] += 1
		invoice = Invoice.sync_from_stripe_data(invoice_data)

		self.assertIsNotNone(invoice)
		self.assertEqual(2, len(invoice.invoiceitems.all()))

		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Subscription.pending_setup_intent",
			},
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
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_invoice_plan_from_invoice_items(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice = Invoice.sync_from_stripe_data(invoice_data)

		self.assertIsNotNone(invoice.plan)  # retrieved from invoice item
		self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Subscription.pending_setup_intent",
			},
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
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_invoice_plan_from_subscription(
		self,
		product_retrieve_mock,
		payment_intent_retrieve_mock,
		charge_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice_data["lines"]["data"][0]["plan"] = None
		invoice = Invoice.sync_from_stripe_data(invoice_data)
		self.assertIsNotNone(invoice.plan)  # retrieved from subscription
		self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Subscription.pending_setup_intent",
			},
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
	@patch("stripe.Subscription.retrieve", autospec=True)
	@patch(
		"stripe.PaymentIntent.retrieve",
		return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
		autospec=True,
	)
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
	def test_invoice_without_plan(
		self,
		charge_retrieve_mock,
		payment_intent_retrieve_mock,
		subscription_retrieve_mock,
		balance_transaction_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoice_data = deepcopy(FAKE_INVOICE)
		invoice_data["lines"]["data"][0]["plan"] = None
		invoice_data["lines"]["data"][0]["subscription"] = None
		invoice_data["subscription"] = None
		invoice = Invoice.sync_from_stripe_data(invoice_data)
		self.assertIsNone(invoice.plan)

		self.assert_fks(
			invoice,
			expected_blank_fks={
				"djstripe.Account.branding_logo",
				"djstripe.Account.branding_icon",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.Invoice.subscription",
				"djstripe.PaymentIntent.on_behalf_of",
				"djstripe.PaymentIntent.payment_method",
				"djstripe.Plan.product",
				"djstripe.Subscription.pending_setup_intent",
			},
		)

	@patch(
		"stripe.Plan.retrieve",
		return_value=deepcopy(FAKE_PLAN),
		autospec=IS_ASSERT_CALLED_AUTOSPEC_SUPPORTED,
	)
	@patch(
		"stripe.Subscription.retrieve",
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch(
		"stripe.Invoice.upcoming",
		return_value=deepcopy(FAKE_UPCOMING_INVOICE),
		autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_upcoming_invoice(
		self,
		product_retrieve_mock,
		invoice_upcoming_mock,
		subscription_retrieve_mock,
		plan_retrieve_mock,
	):
		invoice = UpcomingInvoice.upcoming()
		self.assertIsNotNone(invoice)
		self.assertIsNone(invoice.id)
		self.assertIsNone(invoice.save())
		self.assertEqual(invoice.get_stripe_dashboard_url(), "")

		subscription_retrieve_mock.assert_called_once_with(
			api_key=ANY, expand=ANY, id=FAKE_SUBSCRIPTION["id"]
		)
		plan_retrieve_mock.assert_not_called()

		items = invoice.invoiceitems.all()
		self.assertEqual(1, len(items))
		self.assertEqual(FAKE_SUBSCRIPTION["id"], items[0].id)

		# delete/update should do nothing
		self.assertEqual(invoice.invoiceitems.update(), 0)
		self.assertEqual(invoice.invoiceitems.delete(), 0)

		self.assertIsNotNone(invoice.plan)
		self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

		invoice._invoiceitems = []
		items = invoice.invoiceitems.all()
		self.assertEqual(0, len(items))
		self.assertIsNotNone(invoice.plan)

	@patch("stripe.Plan.retrieve", autospec=IS_ASSERT_CALLED_AUTOSPEC_SUPPORTED)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	@patch(
		"stripe.Subscription.retrieve",
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch(
		"stripe.Invoice.upcoming",
		return_value=deepcopy(FAKE_UPCOMING_INVOICE),
		autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
	)
	def test_upcoming_invoice_with_subscription(
		self,
		invoice_upcoming_mock,
		subscription_retrieve_mock,
		product_retrieve_mock,
		plan_retrieve_mock,
	):
		invoice = Invoice.upcoming(subscription=Subscription(id=FAKE_SUBSCRIPTION["id"]))
		self.assertIsNotNone(invoice)
		self.assertIsNone(invoice.id)
		self.assertIsNone(invoice.save())

		subscription_retrieve_mock.assert_called_once_with(
			api_key=ANY, expand=ANY, id=FAKE_SUBSCRIPTION["id"]
		)
		plan_retrieve_mock.assert_not_called()

		self.assertIsNotNone(invoice.plan)
		self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

	@patch("stripe.Plan.retrieve", autospec=IS_ASSERT_CALLED_AUTOSPEC_SUPPORTED)
	@patch(
		"stripe.Subscription.retrieve",
		return_value=deepcopy(FAKE_SUBSCRIPTION),
		autospec=True,
	)
	@patch(
		"stripe.Invoice.upcoming",
		return_value=deepcopy(FAKE_UPCOMING_INVOICE),
		autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
	)
	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True)
	def test_upcoming_invoice_with_subscription_plan(
		self,
		product_retrieve_mock,
		invoice_upcoming_mock,
		subscription_retrieve_mock,
		plan_retrieve_mock,
	):
		invoice = Invoice.upcoming(subscription_plan=Plan(id=FAKE_PLAN["id"]))
		self.assertIsNotNone(invoice)
		self.assertIsNone(invoice.id)
		self.assertIsNone(invoice.save())

		subscription_retrieve_mock.assert_called_once_with(
			api_key=ANY, expand=ANY, id=FAKE_SUBSCRIPTION["id"]
		)
		plan_retrieve_mock.assert_not_called()

		self.assertIsNotNone(invoice.plan)
		self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

	@patch(
		"stripe.Invoice.upcoming",
		side_effect=InvalidRequestError("Nothing to invoice for customer", None),
	)
	def test_no_upcoming_invoices(self, invoice_upcoming_mock):
		invoice = Invoice.upcoming()
		self.assertIsNone(invoice)

	@patch(
		"stripe.Invoice.upcoming", side_effect=InvalidRequestError("Some other error", None)
	)
	def test_upcoming_invoice_error(self, invoice_upcoming_mock):
		with self.assertRaises(InvalidRequestError):
			Invoice.upcoming()
