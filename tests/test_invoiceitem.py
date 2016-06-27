"""
.. module:: dj-stripe.tests.test_invoiceitem
   :synopsis: dj-stripe InvoiceItem Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test.testcases import TestCase
from mock import patch

from djstripe.models import Customer, InvoiceItem, Account
from tests import FAKE_INVOICEITEM, FAKE_INVOICE_II, FAKE_CHARGE_II, FAKE_CUSTOMER_II, FAKE_SUBSCRIPTION_III, FAKE_PLAN_II


class InvoiceItemTest(TestCase):

    def setUp(self):
        self.account = Account.objects.create()

        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER_II["id"], currency="usd")

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION_III))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_II))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II))
    @patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II))
    def test_str(self, invoice_retrieve_mock, charge_retrieve_mock, customer_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

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
    def test_sync_with_subscription(self, invoice_retrieve_mock, charge_retrieve_mock, customer_retrieve_mock, subscription_retrieve_mock, default_account_mock):
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
    def test_sync_proration(self, invoice_retrieve_mock, charge_retrieve_mock, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        invoiceitem_data.update({"proration": True, "plan": FAKE_PLAN_II["id"]})
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        self.assertEqual(FAKE_PLAN_II["id"], invoiceitem.plan.stripe_id)
