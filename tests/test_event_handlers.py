"""
.. module:: dj-stripe.tests.test_event_handlers
   :synopsis: dj-stripe Event Handler Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
import decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from mock import patch

from djstripe.models import Event, Charge, Transfer, Account, Plan, Customer, InvoiceItem, Invoice
from tests import (FAKE_CUSTOMER, FAKE_CUSTOMER_II, FAKE_EVENT_CHARGE_SUCCEEDED, FAKE_EVENT_TRANSFER_CREATED,
                   FAKE_EVENT_PLAN_CREATED, FAKE_CHARGE, FAKE_CHARGE_II, FAKE_INVOICE_II, FAKE_EVENT_INVOICEITEM_CREATED,
                   FAKE_EVENT_INVOICE_CREATED)


class TestChargeEvents(TestCase):

    @patch("djstripe.models.Account.get_default_account")
    @patch('stripe.Customer.retrieve', return_value=deepcopy(FAKE_CUSTOMER))
    @patch('stripe.Charge.retrieve')
    @patch("stripe.Event.retrieve")
    def test_charge_created(self, event_retrieve_mock, charge_retrieve_mock, customer_retrieve_mock, account_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_CHARGE_SUCCEEDED)
        event_retrieve_mock.return_value = fake_stripe_event
        charge_retrieve_mock.return_value = fake_stripe_event["data"]["object"]
        account_mock.return_value = Account.objects.create()

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        charge = Charge.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEquals(charge.amount, fake_stripe_event["data"]["object"]["amount"] / decimal.Decimal("100"))
        self.assertEquals(charge.status, fake_stripe_event["data"]["object"]["status"])


class TestCustomerEvents(TestCase):

    def test_customer_created(self):
        pass

class TestInvoiceEvents(TestCase):

    @patch("djstripe.models.Charge.send_receipt", autospec=True)
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    @patch("stripe.Invoice.retrieve")
    @patch("stripe.Event.retrieve")
    def test_invoice_created(self, event_retrieve_mock, invoice_retrieve_mock, charge_retrieve_mock,
                             customer_retrieve_mock, default_account_mock, send_receipt_mock):
        default_account_mock.return_value = Account.objects.create()

        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        Customer.objects.create(subscriber=user, stripe_id="cus_4UbFSo9tl62jqj", currency="usd")

        fake_stripe_event = deepcopy(FAKE_EVENT_INVOICE_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event

        invoice_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        invoice = Invoice.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEquals(invoice.amount_due, fake_stripe_event["data"]["object"]["amount_due"] / decimal.Decimal("100"))
        self.assertEquals(invoice.paid, fake_stripe_event["data"]["object"]["paid"])


class TestInvoiceItemEvents(TestCase):

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_II))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II))
    @patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II))
    @patch("stripe.InvoiceItem.retrieve")
    @patch("stripe.Event.retrieve")
    def test_invoiceitem_created(self, event_retrieve_mock, invoiceitem_retrieve_mock, invoice_retrieve_mock,
                                 charge_retrieve_mock, customer_retrieve_mock, default_account_mock):
        default_account_mock.return_value = Account.objects.create()

        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        Customer.objects.create(subscriber=user, stripe_id="cus_4UbFSo9tl62jqj", currency="usd")

        fake_stripe_event = deepcopy(FAKE_EVENT_INVOICEITEM_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event

        invoiceitem_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        invoiceitem = InvoiceItem.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEquals(invoiceitem.amount, fake_stripe_event["data"]["object"]["amount"] / decimal.Decimal("100"))


class TestPlanEvents(TestCase):

    @patch('stripe.Plan.retrieve')
    @patch("stripe.Event.retrieve")
    def test_plan_created(self, event_retrieve_mock, plan_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_PLAN_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event
        plan_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        plan = Plan.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEquals(plan.name, fake_stripe_event["data"]["object"]["name"])


class TestTransferEvents(TestCase):

    @patch('stripe.Transfer.retrieve')
    @patch("stripe.Event.retrieve")
    def test_transfer_created(self, event_retrieve_mock, transfer_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event
        transfer_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        transfer = Transfer.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEquals(transfer.amount, fake_stripe_event["data"]["object"]["amount"] / decimal.Decimal("100"))
        self.assertEquals(transfer.status, fake_stripe_event["data"]["object"]["status"])
