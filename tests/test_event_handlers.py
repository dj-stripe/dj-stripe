"""
.. module:: dj-stripe.tests.test_event_handlers
   :synopsis: dj-stripe Event Handler Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

"""

import decimal
from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import TestCase
from mock import patch

from djstripe.models import (
    Account, Card, Charge, Coupon, Customer, Event, Invoice,
    InvoiceItem, Plan, Subscription, Transfer
)
from tests import (
    FAKE_CARD, FAKE_CHARGE, FAKE_CHARGE_II, FAKE_COUPON, FAKE_CUSTOMER, FAKE_CUSTOMER_II,
    FAKE_EVENT_ACCOUNT_APPLICATION_DEAUTHORIZED, FAKE_EVENT_CHARGE_SUCCEEDED,
    FAKE_EVENT_CUSTOMER_CREATED, FAKE_EVENT_CUSTOMER_DELETED,
    FAKE_EVENT_CUSTOMER_DISCOUNT_CREATED, FAKE_EVENT_CUSTOMER_DISCOUNT_DELETED,
    FAKE_EVENT_CUSTOMER_SOURCE_CREATED, FAKE_EVENT_CUSTOMER_SOURCE_DELETED,
    FAKE_EVENT_CUSTOMER_SOURCE_DELETED_DUPE,
    FAKE_EVENT_CUSTOMER_SUBSCRIPTION_CREATED, FAKE_EVENT_CUSTOMER_SUBSCRIPTION_DELETED,
    FAKE_EVENT_INVOICEITEM_CREATED, FAKE_EVENT_INVOICEITEM_DELETED,
    FAKE_EVENT_INVOICE_CREATED, FAKE_EVENT_INVOICE_DELETED,
    FAKE_EVENT_PLAN_CREATED, FAKE_EVENT_PLAN_DELETED,
    FAKE_EVENT_TRANSFER_CREATED, FAKE_EVENT_TRANSFER_DELETED,
    FAKE_INVOICE, FAKE_INVOICEITEM, FAKE_INVOICE_II, FAKE_PLAN,
    FAKE_SUBSCRIPTION, FAKE_SUBSCRIPTION_III, FAKE_TRANSFER
)


class EventTestCase(TestCase):
    #
    # Helpers
    #

    @patch('stripe.Event.retrieve')
    def _create_event(self, event_data, event_retrieve_mock, patch_data=None):
        event_data = deepcopy(event_data)

        if patch_data:
            event_data.update(patch_data)

        event_retrieve_mock.return_value = event_data
        event = Event.sync_from_stripe_data(event_data)
        event.validate()

        return event


class TestAccountEvents(EventTestCase):
    @patch("stripe.Event.retrieve")
    def test_account_deauthorized_event(self, event_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_ACCOUNT_APPLICATION_DEAUTHORIZED)

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.validate()
        event.process()


class TestChargeEvents(EventTestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")

    @patch("djstripe.models.Account.get_default_account")
    @patch('stripe.Customer.retrieve', return_value=deepcopy(FAKE_CUSTOMER))
    @patch('stripe.Charge.retrieve')
    @patch("stripe.Event.retrieve")
    def test_charge_created(self, event_retrieve_mock, charge_retrieve_mock, customer_retrieve_mock, account_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_CHARGE_SUCCEEDED)
        event_retrieve_mock.return_value = fake_stripe_event
        charge_retrieve_mock.return_value = fake_stripe_event["data"]["object"]
        account_mock.return_value = Account.objects.create()

        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        charge = Charge.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(charge.amount, fake_stripe_event["data"]["object"]["amount"] / decimal.Decimal("100"))
        self.assertEqual(charge.status, fake_stripe_event["data"]["object"]["status"])


class TestCustomerEvents(EventTestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")

    @patch("stripe.Customer.retrieve")
    @patch("stripe.Event.retrieve")
    def test_customer_created(self, event_retrieve_mock, customer_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event
        customer_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        customer = Customer.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(customer.account_balance, fake_stripe_event["data"]["object"]["account_balance"])
        self.assertEqual(customer.currency, fake_stripe_event["data"]["object"]["currency"])

    @patch("stripe.Customer.retrieve")
    @patch("stripe.Event.retrieve")
    def test_customer_created_no_customer_exists(self, event_retrieve_mock, customer_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event
        customer_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        self.assertFalse(Customer.objects.filter(stripe_id=fake_stripe_event["data"]["object"]["id"]).exists())

    @patch("stripe.Customer.retrieve", return_value=FAKE_CUSTOMER)
    def test_customer_deleted(self, customer_retrieve_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        event = self._create_event(FAKE_EVENT_CUSTOMER_CREATED)
        self.assertTrue(event.process())

        event = self._create_event(FAKE_EVENT_CUSTOMER_DELETED)
        self.assertTrue(event.process())

        customer = Customer.objects.get(stripe_id=FAKE_CUSTOMER["id"])
        self.assertIsNotNone(customer.date_purged)

    @patch("stripe.Coupon.retrieve", return_value=FAKE_COUPON)
    @patch("stripe.Event.retrieve", return_value=FAKE_EVENT_CUSTOMER_DISCOUNT_CREATED)
    def test_customer_discount_created(self, event_retrieve_mock, coupon_retrieve_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)

        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_DISCOUNT_CREATED)
        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.validate()
        event.process()
        self.assertTrue(event.processed)

        self.assertIsNotNone(event.customer)
        self.assertEqual(event.customer.stripe_id, FAKE_CUSTOMER["id"])
        self.assertIsNotNone(event.customer.coupon)

    @patch("stripe.Coupon.retrieve", return_value=FAKE_COUPON)
    @patch("stripe.Event.retrieve", return_value=FAKE_EVENT_CUSTOMER_DISCOUNT_DELETED)
    def test_customer_discount_deleted(self, event_retrieve_mock, coupon_retrieve_mock):
        customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        coupon = Coupon.sync_from_stripe_data(FAKE_COUPON)
        customer.coupon = coupon

        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_DISCOUNT_DELETED)
        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.validate()
        event.process()
        self.assertTrue(event.processed)

        self.assertIsNotNone(event.customer)
        self.assertEqual(event.customer.stripe_id, FAKE_CUSTOMER["id"])
        self.assertIsNone(event.customer.coupon)

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Event.retrieve")
    def test_customer_card_created(self, event_retrieve_mock, customer_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_SOURCE_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event

        customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.validate()
        event.process()

        card = Card.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertIn(card, customer.sources.all())
        self.assertEqual(card.brand, fake_stripe_event["data"]["object"]["brand"])
        self.assertEqual(card.last4, fake_stripe_event["data"]["object"]["last4"])

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Event.retrieve")
    def test_customer_unknown_source_created(self, event_retrieve_mock, customer_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_SOURCE_CREATED)
        fake_stripe_event["data"]["object"]["object"] = "unknown"
        event_retrieve_mock.return_value = fake_stripe_event

        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)

        event = Event.sync_from_stripe_data(fake_stripe_event)
        event.validate()
        event.process()

        self.assertFalse(Card.objects.filter(stripe_id=fake_stripe_event["data"]["object"]["id"]).exists())

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_customer_default_source_deleted(self, customer_retrieve_mock):
        event = self._create_event(FAKE_EVENT_CUSTOMER_SOURCE_CREATED)
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        self.assertTrue(event.process())

        card = Card.objects.get(stripe_id=FAKE_CARD["id"])
        customer = Customer.objects.get(stripe_id=FAKE_CUSTOMER["id"])
        customer.default_source = card
        customer.save()
        self.assertIsNotNone(customer.default_source)
        self.assertTrue(customer.has_valid_source())

        event = self._create_event(FAKE_EVENT_CUSTOMER_SOURCE_DELETED)
        self.assertTrue(event.process())

        customer = Customer.objects.get(stripe_id=FAKE_CUSTOMER["id"])
        self.assertIsNone(customer.default_source)
        self.assertFalse(customer.has_valid_source())

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_customer_source_double_delete(self, customer_retrieve_mock):
        event = self._create_event(FAKE_EVENT_CUSTOMER_SOURCE_CREATED)
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        self.assertTrue(event.process())

        event = self._create_event(FAKE_EVENT_CUSTOMER_SOURCE_DELETED)
        self.assertTrue(event.process())

        event = self._create_event(FAKE_EVENT_CUSTOMER_SOURCE_DELETED_DUPE)
        self.assertTrue(event.process())

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Event.retrieve")
    def test_customer_subscription_created(self, event_retrieve_mock, customer_retrieve_mock,
                                           subscription_retrieve_mock, plan_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_SUBSCRIPTION_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event

        customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        subscription = Subscription.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertIn(subscription, customer.subscriptions.all())
        self.assertEqual(subscription.status, fake_stripe_event["data"]["object"]["status"])
        self.assertEqual(subscription.quantity, fake_stripe_event["data"]["object"]["quantity"])

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_customer_subscription_deleted(
            self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        event = self._create_event(FAKE_EVENT_CUSTOMER_SUBSCRIPTION_CREATED)
        self.assertTrue(event.process())

        Subscription.objects.get(stripe_id=FAKE_SUBSCRIPTION["id"])

        event = self._create_event(FAKE_EVENT_CUSTOMER_SUBSCRIPTION_DELETED)
        self.assertTrue(event.process())

        with self.assertRaises(Subscription.DoesNotExist):
            Subscription.objects.get(stripe_id=FAKE_SUBSCRIPTION["id"])

    @patch("stripe.Customer.retrieve")
    @patch("stripe.Event.retrieve")
    def test_customer_bogus_event_type(self, event_retrieve_mock, customer_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_CUSTOMER_CREATED)
        fake_stripe_event["data"]["object"]["customer"] = fake_stripe_event["data"]["object"]["id"]
        fake_stripe_event["type"] = "customer.praised"

        event_retrieve_mock.return_value = fake_stripe_event
        customer_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        customer = Customer.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(None, customer.account_balance)


class TestInvoiceEvents(EventTestCase):

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    @patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE))
    @patch("stripe.Event.retrieve")
    def test_invoice_created_no_existing_customer(self, event_retrieve_mock, invoice_retrieve_mock,
                                                  charge_retrieve_mock, customer_retrieve_mock,
                                                  subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = Account.objects.create()

        fake_stripe_event = deepcopy(FAKE_EVENT_INVOICE_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event

        invoice_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()
        self.assertEqual(Customer.objects.count(), 1)
        customer = Customer.objects.get()
        self.assertEqual(customer.subscriber, None)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    @patch("stripe.Invoice.retrieve")
    @patch("stripe.Event.retrieve")
    def test_invoice_created(self, event_retrieve_mock, invoice_retrieve_mock, charge_retrieve_mock,
                             customer_retrieve_mock, subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = Account.objects.create()

        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)

        fake_stripe_event = deepcopy(FAKE_EVENT_INVOICE_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event

        invoice_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        invoice = Invoice.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(
            invoice.amount_due,
            fake_stripe_event["data"]["object"]["amount_due"] / decimal.Decimal("100")
        )
        self.assertEqual(invoice.paid, fake_stripe_event["data"]["object"]["paid"])

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    @patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE))
    def test_invoice_deleted(self, invoice_retrieve_mock, charge_retrieve_mock, customer_retrieve_mock,
                             subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = Account.objects.create()

        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)

        event = self._create_event(FAKE_EVENT_INVOICE_CREATED)
        self.assertTrue(event.process())

        Invoice.objects.get(stripe_id=FAKE_INVOICE["id"])

        event = self._create_event(FAKE_EVENT_INVOICE_DELETED)
        self.assertTrue(event.process())

        with self.assertRaises(Invoice.DoesNotExist):
            Invoice.objects.get(stripe_id=FAKE_INVOICE["id"])


class TestInvoiceItemEvents(EventTestCase):

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION_III))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_II))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II))
    @patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II))
    @patch("stripe.InvoiceItem.retrieve")
    @patch("stripe.Event.retrieve")
    def test_invoiceitem_created(self, event_retrieve_mock, invoiceitem_retrieve_mock, invoice_retrieve_mock,
                                 charge_retrieve_mock, customer_retrieve_mock, subscription_retrieve_mock,
                                 default_account_mock):
        default_account_mock.return_value = Account.objects.create()

        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER_II["id"], livemode=False)

        fake_stripe_event = deepcopy(FAKE_EVENT_INVOICEITEM_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event

        invoiceitem_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        invoiceitem = InvoiceItem.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEqual(invoiceitem.amount, fake_stripe_event["data"]["object"]["amount"] / decimal.Decimal("100"))

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION_III))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_II))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II))
    @patch("stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II))
    @patch("stripe.InvoiceItem.retrieve", return_value=deepcopy(FAKE_INVOICEITEM))
    def test_invoiceitem_deleted(
            self, invoiceitem_retrieve_mock, invoice_retrieve_mock,
            charge_retrieve_mock, customer_retrieve_mock,
            subscription_retrieve_mock, default_account_mock):
        default_account_mock.return_value = Account.objects.create()

        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER_II["id"], livemode=False)

        event = self._create_event(FAKE_EVENT_INVOICEITEM_CREATED)
        self.assertTrue(event.process())

        InvoiceItem.objects.get(stripe_id=FAKE_INVOICEITEM["id"])

        event = self._create_event(FAKE_EVENT_INVOICEITEM_DELETED)
        self.assertTrue(event.process())

        with self.assertRaises(InvoiceItem.DoesNotExist):
            InvoiceItem.objects.get(stripe_id=FAKE_INVOICEITEM["id"])


class TestPlanEvents(EventTestCase):

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
        self.assertEqual(plan.name, fake_stripe_event["data"]["object"]["name"])

    @patch('stripe.Plan.retrieve', return_value=FAKE_PLAN)
    def test_plan_deleted(self, plan_retrieve_mock):
        event = self._create_event(FAKE_EVENT_PLAN_CREATED)
        self.assertTrue(event.process())

        Plan.objects.get(stripe_id=FAKE_PLAN["id"])

        event = self._create_event(FAKE_EVENT_PLAN_DELETED)
        self.assertTrue(event.process())

        with self.assertRaises(Plan.DoesNotExist):
            Plan.objects.get(stripe_id=FAKE_PLAN["id"])


class TestTransferEvents(EventTestCase):

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
        self.assertEqual(transfer.amount, fake_stripe_event["data"]["object"]["amount"] / decimal.Decimal("100"))
        self.assertEqual(transfer.status, fake_stripe_event["data"]["object"]["status"])

    @patch('stripe.Transfer.retrieve', return_value=FAKE_TRANSFER)
    def test_transfer_deleted(self, transfer_retrieve_mock):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)
        self.assertTrue(event.process())

        Transfer.objects.get(stripe_id=FAKE_TRANSFER["id"])

        event = self._create_event(FAKE_EVENT_TRANSFER_DELETED)
        self.assertTrue(event.process())

        with self.assertRaises(Transfer.DoesNotExist):
            Transfer.objects.get(stripe_id=FAKE_TRANSFER["id"])
