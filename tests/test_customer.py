"""
.. module:: dj-stripe.tests.test_customer
   :synopsis: dj-stripe Customer Model Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Michael Thornhill (@mthornhill)

"""

from copy import deepcopy
import datetime
import decimal
from unittest.case import skip

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from mock import patch, PropertyMock, MagicMock
from stripe.error import InvalidRequestError

from djstripe.models import Account, Customer, Charge, Card, Subscription, Invoice, Plan
from tests import (FAKE_CARD, FAKE_CHARGE, FAKE_CUSTOMER, FAKE_ACCOUNT, FAKE_INVOICE, FAKE_INVOICE_II,
                   FAKE_INVOICE_III, FAKE_INVOICEITEM, FAKE_PLAN, FAKE_SUBSCRIPTION, FAKE_SUBSCRIPTION_II,
                   StripeList)


class TestCustomer(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        self.customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

        self.card, _created = Card.get_or_create_from_stripe_object(data=FAKE_CARD)

        self.customer.default_source = self.card
        self.customer.save()

        self.account = Account.objects.create()

    def test_str(self):
        self.assertEqual("<{subscriber}, email={email}, stripe_id={stripe_id}>".format(
            subscriber=str(self.user), email=self.user.email, stripe_id=FAKE_CUSTOMER["id"]
        ), str(self.customer))

    @patch("stripe.Customer.retrieve")
    def test_customer_purge_leaves_customer_record(self, customer_retrieve_fake):
        self.customer.purge()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)

        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.default_source is None)
        self.assertTrue(not customer.sources.all())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    @patch("stripe.Customer.retrieve")
    def test_customer_delete_same_as_purge(self, customer_retrieve_fake):
        self.customer.delete()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.default_source is None)
        self.assertTrue(not customer.sources.all())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    @patch("stripe.Customer.retrieve")
    def test_customer_purge_raises_customer_exception(self, customer_retrieve_mock):
        customer_retrieve_mock.side_effect = InvalidRequestError("No such customer:", "blah")

        self.customer.purge()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.default_source is None)
        self.assertTrue(not customer.sources.all())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

        customer_retrieve_mock.assert_called_with(id=self.customer.stripe_id, api_key=settings.STRIPE_SECRET_KEY, expand=None)
        self.assertEquals(2, customer_retrieve_mock.call_count)

    @patch("stripe.Customer.retrieve")
    def test_customer_delete_raises_unexpected_exception(self, customer_retrieve_mock):
        customer_retrieve_mock.side_effect = InvalidRequestError("Unexpected Exception", "blah")

        with self.assertRaisesMessage(InvalidRequestError, "Unexpected Exception"):
            self.customer.purge()

        customer_retrieve_mock.assert_called_once_with(id=self.customer.stripe_id, api_key=settings.STRIPE_SECRET_KEY, expand=None)

    def test_can_charge(self):
        self.assertTrue(self.customer.can_charge())

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_add_card_set_default_true(self, customer_retrieve_mock):
        self.customer.add_card(FAKE_CARD["id"])

        customer_retrieve_mock.assert_called_once_with(id=self.customer.stripe_id, api_key=settings.STRIPE_SECRET_KEY, expand=None)

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_add_card_set_default_false(self, customer_retrieve_mock):
        self.customer.add_card(FAKE_CARD["id"], set_default=False)

        customer_retrieve_mock.assert_called_once_with(id=self.customer.stripe_id, api_key=settings.STRIPE_SECRET_KEY, expand=None)

    @patch("stripe.Customer.retrieve")
    def test_cannot_charge(self, customer_retrieve_fake):
        self.customer.delete()
        self.assertFalse(self.customer.can_charge())

    def test_charge_accepts_only_decimals(self):
        with self.assertRaises(ValueError):
            self.customer.charge(10)

    @skip
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    def test_refund_charge(self, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_no_invoice = deepcopy(FAKE_CHARGE)
        fake_charge_no_invoice.update({"invoice": None})

        charge_retrieve_mock.return_value = fake_charge_no_invoice

        charge, created = Charge.get_or_create_from_stripe_object(fake_charge_no_invoice)
        self.assertTrue(created)

        charge.refund()

        refunded_charge, created2 = Charge.get_or_create_from_stripe_object(fake_charge_no_invoice)
        self.assertFalse(created2)

        self.assertEquals(refunded_charge.refunded, True)
        self.assertEquals(refunded_charge.amount_refunded, decimal.Decimal("22.00"))

    @skip
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    def test_refund_charge_object_returned(self, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_no_invoice = deepcopy(FAKE_CHARGE)
        fake_charge_no_invoice.update({"invoice": None})

        charge_retrieve_mock.return_value = fake_charge_no_invoice

        charge, created = Charge.get_or_create_from_stripe_object(fake_charge_no_invoice)
        self.assertTrue(created)

        refunded_charge = charge.refund()
        self.assertEquals(refunded_charge.refunded, True)
        self.assertEquals(refunded_charge.amount_refunded, decimal.Decimal("22.00"))

    @skip
    def test_calculate_refund_amount_full_refund(self):
        charge = Charge(
            stripe_id="ch_111111",
            customer=self.customer,
            amount=decimal.Decimal("500.00")
        )
        self.assertEquals(charge._calculate_refund_amount(), 50000)

    @skip
    def test_calculate_refund_amount_partial_refund(self):
        charge = Charge(
            stripe_id="ch_111111",
            customer=self.customer,
            amount=decimal.Decimal("500.00")
        )
        self.assertEquals(
            charge._calculate_refund_amount(amount=decimal.Decimal("300.00")),
            30000
        )

    @skip
    def test_calculate_refund_above_max_refund(self):
        charge = Charge(
            stripe_id="ch_111111",
            customer=self.customer,
            amount=decimal.Decimal("500.00")
        )
        self.assertEquals(
            charge._calculate_refund_amount(amount=decimal.Decimal("600.00")),
            50000
        )

    @skip
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    def test_charge_converts_dollars_into_cents(self, charge_create_mock, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": None, "amount": 1000})

        charge_create_mock.return_value = fake_charge_copy
        charge_retrieve_mock.return_value = fake_charge_copy

        self.customer.charge(amount=decimal.Decimal("10.00"))

        _, kwargs = charge_create_mock.call_args
        self.assertEquals(kwargs["amount"], 1000)

    @skip
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    @patch("stripe.Invoice.retrieve")
    def test_charge_doesnt_require_invoice(self, invoice_retrieve_mock, charge_create_mock, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": "in_16YHls2eZvKYlo2CwwH968Mc", "amount": 2000})
        fake_invoice_copy = deepcopy(FAKE_INVOICE)

        charge_create_mock.return_value = fake_charge_copy
        charge_retrieve_mock.return_value = fake_charge_copy
        invoice_retrieve_mock.return_value = fake_invoice_copy

        try:
            self.customer.charge(amount=decimal.Decimal("20.00"))
        except Invoice.DoesNotExist:
            self.fail(msg="Stripe Charge shouldn't throw Invoice DoesNotExist.")

    @skip
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    def test_charge_passes_extra_arguments(self, charge_create_mock, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": None})

        charge_create_mock.return_value = fake_charge_copy
        charge_retrieve_mock.return_value = fake_charge_copy

        self.customer.charge(
            amount=decimal.Decimal("10.00"),
            capture=True,
            destination=PropertyMock(stripe_id=FAKE_ACCOUNT["id"]),
        )

        _, kwargs = charge_create_mock.call_args
        self.assertEquals(kwargs["capture"], True)
        self.assertEquals(kwargs["destination"], FAKE_ACCOUNT["id"])

    @skip
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    def test_charge_string_source(self, charge_create_mock, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": None})

        charge_create_mock.return_value = fake_charge_copy
        charge_retrieve_mock.return_value = fake_charge_copy

        self.customer.charge(
            amount=decimal.Decimal("10.00"),
            source=self.card.stripe_id,
        )

    @skip
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    def test_charge_card_source(self, charge_create_mock, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": None})

        charge_create_mock.return_value = fake_charge_copy
        charge_retrieve_mock.return_value = fake_charge_copy

        self.customer.charge(
            amount=decimal.Decimal("10.00"),
            source=self.card,
        )

    @skip
    @patch("djstripe.models.djstripe_settings.trial_period_for_subscriber_callback", return_value="donkey")
    @patch("stripe.Customer.create", return_value=PropertyMock(id="cus_xxx1234567890"))
    def test_create_trial_callback(self, customer_create_mock, callback_mock):
        user = get_user_model().objects.create_user(username="test", email="test@gmail.com")
        Customer.create(user)

        customer_create_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, email=user.email)
        callback_mock.assert_called_once_with(user)

    @skip
    @patch("djstripe.models.Customer.subscribe")
    @patch("djstripe.models.djstripe_settings.DEFAULT_PLAN", new_callable=PropertyMock, return_value="schreck")
    @patch("djstripe.models.djstripe_settings.trial_period_for_subscriber_callback", return_value="donkey")
    @patch("stripe.Customer.create", return_value=PropertyMock(id="cus_xxx1234567890"))
    def test_create_default_plan(self, customer_create_mock, callback_mock, default_plan_fake, subscribe_mock):
        user = get_user_model().objects.create_user(username="test", email="test@gmail.com")
        Customer.create(user)

        customer_create_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, email=user.email)
        callback_mock.assert_called_once_with(user)
        subscribe_mock.assert_called_once_with(plan=default_plan_fake, trial_days="donkey")

    @skip
    # TODO Add retry, filter? to CustomerDict mock
    @patch("djstripe.models.Customer.invoices", new_callable=PropertyMock,
           return_value=PropertyMock(name="filter", filter=MagicMock(return_value=[MagicMock(name="inv", retry=MagicMock(name="retry", return_value="test"))])))
    @patch("djstripe.models.Customer._sync_invoices")
    def test_retry_unpaid_invoices(self, _sync_invoices_mock, invoices_mock):
        self.customer.retry_unpaid_invoices()

        _sync_invoices_mock.assert_called_once_with()

    @skip
    @patch("djstripe.models.Customer.invoices", new_callable=PropertyMock,
       return_value=PropertyMock(name="filter", filter=MagicMock(return_value=[MagicMock(name="inv", retry=MagicMock(name="retry",
                                                                                                                     return_value="test",
                                                                                                                     side_effect=InvalidRequestError("Invoice is already paid", "blah")))])))
    @patch("djstripe.models.Customer._sync_invoices")
    def test_retry_unpaid_invoices_expected_exception(self, _sync_invoices_mock, invoices_mock):
        try:
            self.customer.retry_unpaid_invoices()
        except:
            self.fail("Exception was unexpectedly raise.")

    @skip
    @patch("djstripe.models.Customer.invoices", new_callable=PropertyMock,
       return_value=PropertyMock(name="filter", filter=MagicMock(return_value=[MagicMock(name="inv", retry=MagicMock(name="retry",
                                                                                                                     return_value="test",
                                                                                                                     side_effect=InvalidRequestError("This should fail!", "blah")))])))
    @patch("djstripe.models.Customer._sync_invoices")
    def test_retry_unpaid_invoices_unexpected_exception(self, _sync_invoices_mock, invoices_mock):
        with self.assertRaisesMessage(InvalidRequestError, "This should fail!"):
            self.customer.retry_unpaid_invoices()

    @skip
    @patch("stripe.Invoice.create")
    def test_send_invoice_success(self, invoice_create_mock):
        return_status = self.customer.send_invoice()
        self.assertTrue(return_status)

        invoice_create_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, customer=self.customer.stripe_id)

    @skip
    @patch("stripe.Invoice.create")
    def test_send_invoice_failure(self, invoice_create_mock):
        invoice_create_mock.side_effect = InvalidRequestError("Invoice creation failed.", "blah")

        return_status = self.customer.send_invoice()
        self.assertFalse(return_status)

        invoice_create_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, customer=self.customer.stripe_id)

    @skip
    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("djstripe.models.Customer.api_retrieve", return_value=FAKE_CUSTOMER)
    def test_sync_invoices(self, api_retrieve_mock, sync_from_stripe_data_mock):
        self.customer._sync_invoices()

        sync_from_stripe_data_mock.assert_any_call(FAKE_INVOICE)
        sync_from_stripe_data_mock.assert_any_call(FAKE_INVOICE_II)
        sync_from_stripe_data_mock.assert_any_call(FAKE_INVOICE_III)

        self.assertEqual(3, sync_from_stripe_data_mock.call_count)

    @skip
    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("tests.FAKE_CUSTOMER.invoices", return_value=StripeList(data=[]))  # See this for above TODO; probably want to mock CustomerDict though
    @patch("djstripe.models.Customer.api_retrieve")
    def test_sync_invoices_none(self, api_retrieve_mock, customer_invoice_retrieve_mock, sync_from_stripe_data_mock):
        self.customer._sync_invoices()

        self.assertFalse(sync_from_stripe_data_mock.called)

    @skip
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    @patch("djstripe.models.Customer.api_retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_sync_charges(self, api_retrieve_mock, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": None})

        charge_retrieve_mock.return_value = fake_charge_copy

        self.customer._sync_charges()

    @skip
    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    @patch("djstripe.models.Customer.api_retrieve",
           return_value=PropertyMock(charges=MagicMock(return_value=PropertyMock(data=[]))))  # TODO: Fix this to mock CustomerDict
    def test_sync_charges_none(self, api_retrieve_mock, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": None})

        charge_retrieve_mock.return_value = fake_charge_copy

        self.customer._sync_charges()

    @patch("djstripe.models.Subscription.sync_from_stripe_data", autospec=True)
    @patch("stripe.Subscription.list", return_value=StripeList(data=[deepcopy(FAKE_SUBSCRIPTION), deepcopy(FAKE_SUBSCRIPTION_II)]))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_sync_subscriptions(self, customer_retrieve_mock, subscription_list_mock, subscription_sync_mock):
        self.customer._sync_subscriptions()
        self.assertEqual(2, subscription_sync_mock.call_count)

    @patch("djstripe.models.Subscription.sync_from_stripe_data", autospec=True)
    @patch("stripe.Subscription.list", return_value=StripeList(data=[]))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_sync_subscriptions_none(self, customer_retrieve_mock, subscription_list_mock, subscription_sync_mock):
        self.customer._sync_subscriptions()
        self.assertEqual(0, subscription_sync_mock.call_count)

    @patch("djstripe.models.Customer.send_invoice")
    @patch("stripe.Subscription.create", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_subscribe_not_charge_immediately(self, customer_retrieve_mock, subscription_create_mock, send_invoice_mock):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        self.customer.subscribe(plan=plan, charge_immediately=False)
        self.assertFalse(send_invoice_mock.called)

    @patch("djstripe.models.Charge.send_receipt")
    @patch("djstripe.models.Charge.sync_from_stripe_data")
    @patch("stripe.Charge.retrieve", return_value=FAKE_CHARGE)
    @patch("stripe.Charge.create", return_value=FAKE_CHARGE)
    def test_charge_not_send_receipt(self, charge_create_mock, charge_retrieve_mock, charge_sync_mock, send_receipt_mock):
        self.customer.charge(amount=decimal.Decimal("50.00"), send_receipt=False)

        self.assertFalse(charge_retrieve_mock.called)
        self.assertTrue(charge_create_mock.called)
        charge_sync_mock.assert_called_once_with(FAKE_CHARGE)
        self.assertFalse(send_receipt_mock.called)

    @patch("djstripe.models.InvoiceItem.sync_from_stripe_data", return_value="pancakes")
    @patch("stripe.InvoiceItem.create", return_value=deepcopy(FAKE_INVOICEITEM))
    def test_add_invoice_item(self, invoiceitem_create_mock, invoiceitem_sync_mock):
        invoiceitem = self.customer.add_invoice_item(amount=decimal.Decimal("50.00"), currency="eur", description="test", invoice=77, subscription=25)
        self.assertEqual("pancakes", invoiceitem)

        invoiceitem_create_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, amount=5000, customer=self.customer.stripe_id, currency="eur", description="test", discountable=None, invoice=77, metadata=None, subscription=25)

    @patch("djstripe.models.InvoiceItem.sync_from_stripe_data", return_value="pancakes")
    @patch("stripe.InvoiceItem.create", return_value=deepcopy(FAKE_INVOICEITEM))
    def test_add_invoice_item_djstripe_objects(self, invoiceitem_create_mock, invoiceitem_sync_mock):
        invoiceitem = self.customer.add_invoice_item(amount=decimal.Decimal("50.00"), currency="eur", description="test", invoice=Invoice(stripe_id=77), subscription=Subscription(stripe_id=25))
        self.assertEqual("pancakes", invoiceitem)

        invoiceitem_create_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, amount=5000, customer=self.customer.stripe_id, currency="eur", description="test", discountable=None, invoice=77, metadata=None, subscription=25)

    def test_add_invoice_item_bad_decimal(self):
        with self.assertRaisesMessage(ValueError, "You must supply a decimal value representing dollars."):
            self.customer.add_invoice_item(amount=5000, currency="usd")
