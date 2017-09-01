"""
.. module:: dj-stripe.tests.test_invoiceitem
   :synopsis: dj-stripe InvoiceItem Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from copy import deepcopy

from django.test.testcases import TestCase
from mock import patch

from djstripe.models import Account, InvoiceItem

from . import FAKE_CHARGE_II, FAKE_CUSTOMER_II, FAKE_INVOICE_II, FAKE_INVOICEITEM, FAKE_PLAN_II, FAKE_SUBSCRIPTION_III


class InvoiceItemTest(TestCase):

    def setUp(self):
        self.account = Account.objects.create()

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN_II))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION_III))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_II))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II))
    @patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II))
    def test_str(self, invoice_retrieve_mock, charge_retrieve_mock, customer_retrieve_mock, subscription_retrieve_mock,
                 plan_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        invoiceitem_data["plan"] = FAKE_PLAN_II
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)
        self.assertEqual(invoiceitem.get_stripe_dashboard_url(), invoiceitem.invoice.get_stripe_dashboard_url())

        self.assertEqual(
            str(invoiceitem),
            "Subscription to New plan name ({price})".format(price=invoiceitem.plan.human_readable_price)
        )
        invoiceitem.plan = None
        self.assertEqual(str(invoiceitem), "<amount={amount}, date={date}, stripe_id={stripe_id}>".format(
            amount=invoiceitem.amount,
            date=invoiceitem.date,
            stripe_id=invoiceitem_data["id"]
        ))

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION_III))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_II))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II))
    @patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II))
    def test_sync_with_subscription(self, invoice_retrieve_mock, charge_retrieve_mock, customer_retrieve_mock,
                                    subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        invoiceitem_data.update({"subscription": FAKE_SUBSCRIPTION_III["id"]})
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        self.assertEqual(FAKE_SUBSCRIPTION_III["id"], invoiceitem.subscription.stripe_id)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN_II))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION_III))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_II))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II))
    @patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II))
    def test_sync_proration(self, invoice_retrieve_mock, charge_retrieve_mock, customer_retrieve_mock,
                            subscription_retrieve_mock, plan_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        invoiceitem_data.update({"proration": True, "plan": FAKE_PLAN_II["id"]})
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        self.assertEqual(FAKE_PLAN_II["id"], invoiceitem.plan.stripe_id)
