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
from tests import FAKE_INVOICEITEM, FAKE_INVOICE_II, FAKE_CHARGE_II, FAKE_CUSTOMER_II, FAKE_SUBSCRIPTION_III


class InvoiceItemTest(TestCase):

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION_III))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_II))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II))
    @patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II))
    def setUp(self, invoice_retrieve_mock, charge_retrieve_mock, customer_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = Account.objects.create()

        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER_II["id"], currency="usd")

        self.invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        self.invoiceitem = InvoiceItem.sync_from_stripe_data(self.invoiceitem_data)

    def test_str(self):
        self.assertEqual(str(self.invoiceitem), "<amount={amount}, date={date}, stripe_id={stripe_id}>".format(
            amount=self.invoiceitem.amount,
            date=self.invoiceitem.date,
            stripe_id=self.invoiceitem_data["id"]
        ))
