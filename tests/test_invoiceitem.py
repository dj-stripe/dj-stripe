"""
dj-stripe InvoiceItem Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.test.testcases import TestCase

from djstripe.models import InvoiceItem

from . import (
	FAKE_CHARGE_II, FAKE_CUSTOMER_II, FAKE_INVOICE_II, FAKE_INVOICEITEM,
	FAKE_PLAN_II, FAKE_SUBSCRIPTION_III, AssertStripeFksMixin, default_account
)


class InvoiceItemTest(AssertStripeFksMixin, TestCase):
	def setUp(self):
		self.account = default_account()

	@patch("djstripe.models.Account.get_default_account")
	@patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION_III))
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_II))
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II))
	@patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II))
	def test_str(
		self,
		invoice_retrieve_mock,
		charge_retrieve_mock,
		customer_retrieve_mock,
		subscription_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
		invoiceitem_data["plan"] = FAKE_PLAN_II
		invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)
		self.assertEqual(
			invoiceitem.get_stripe_dashboard_url(),
			invoiceitem.invoice.get_stripe_dashboard_url(),
		)

		self.assertEqual(
			str(invoiceitem),
			"<amount=20, date=2015-08-08 11:26:56+00:00, id=ii_16XVTY2eZvKYlo2Cxz5n3RaS>",
		)
		invoiceitem.plan = None
		self.assertEqual(
			str(invoiceitem),
			"<amount=20, date=2015-08-08 11:26:56+00:00, id=ii_16XVTY2eZvKYlo2Cxz5n3RaS>",
		)

	@patch("djstripe.models.Account.get_default_account")
	@patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION_III))
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_II))
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II))
	@patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II))
	def test_sync_with_subscription(
		self,
		invoice_retrieve_mock,
		charge_retrieve_mock,
		customer_retrieve_mock,
		subscription_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
		invoiceitem_data.update({"subscription": FAKE_SUBSCRIPTION_III["id"]})
		invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

		self.assert_fks(
			invoiceitem,
			expected_blank_fks={
				"djstripe.Account.business_logo",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.Customer.subscriber",
				"djstripe.Plan.product",
				"djstripe.InvoiceItem.plan",
			},
		)

	@patch("djstripe.models.Account.get_default_account")
	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN_II))
	@patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION_III))
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_II))
	@patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II))
	@patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II))
	def test_sync_proration(
		self,
		invoice_retrieve_mock,
		charge_retrieve_mock,
		customer_retrieve_mock,
		subscription_retrieve_mock,
		plan_retrieve_mock,
		default_account_mock,
	):
		default_account_mock.return_value = self.account

		invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
		invoiceitem_data.update({"proration": True, "plan": FAKE_PLAN_II["id"]})
		invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

		self.assertEqual(FAKE_PLAN_II["id"], invoiceitem.plan.id)

		self.assert_fks(
			invoiceitem,
			expected_blank_fks={
				"djstripe.Account.business_logo",
				"djstripe.Charge.dispute",
				"djstripe.Charge.transfer",
				"djstripe.Customer.coupon",
				"djstripe.Customer.subscriber",
				"djstripe.InvoiceItem.subscription",
				"djstripe.Plan.product",
			},
		)
