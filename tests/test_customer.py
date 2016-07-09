"""
.. module:: dj-stripe.tests.test_customer
   :synopsis: dj-stripe Customer Model Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Michael Thornhill (@mthornhill)
.. moduleauthor:: Lee Skillen (@lskillen)

"""

from copy import deepcopy
import decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from mock import patch, ANY
from stripe.error import InvalidRequestError

from djstripe.exceptions import MultipleSubscriptionException
from djstripe.models import Account, Customer, Charge, Card, Subscription, Invoice, Plan
from tests import (FAKE_CARD, FAKE_CHARGE, FAKE_CUSTOMER, FAKE_ACCOUNT, FAKE_INVOICE,
                   FAKE_INVOICE_III, FAKE_INVOICEITEM, FAKE_PLAN, FAKE_SUBSCRIPTION, FAKE_SUBSCRIPTION_II,
                   StripeList, FAKE_CARD_V, FAKE_CUSTOMER_II, FAKE_UPCOMING_INVOICE,
    datetime_to_unix)


class TestCustomer(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        self.customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

        self.card, _created = Card._get_or_create_from_stripe_object(data=FAKE_CARD)

        self.customer.default_source = self.card
        self.customer.save()

        self.account = Account.objects.create()

    def test_str(self):
        self.assertEqual("<{subscriber}, email={email}, stripe_id={stripe_id}>".format(
            subscriber=str(self.user), email=self.user.email, stripe_id=FAKE_CUSTOMER["id"]
        ), str(self.customer))

    def test_customer_sync_unsupported_source(self):
        fake_customer = deepcopy(FAKE_CUSTOMER_II)
        fake_customer["default_source"]["object"] = "fish"

        user = get_user_model().objects.create_user(username="testuser", email="testuser@gmail.com")
        Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER_II["id"], currency="usd")

        customer = Customer.sync_from_stripe_data(fake_customer)

        self.assertEqual(None, customer.default_source)
        self.assertEqual(0, customer.sources.count())

    @patch("stripe.Card.retrieve", return_value=FAKE_CUSTOMER_II["default_source"])
    def test_customer_sync_non_local_card(self, card_retrieve_mock):
        fake_customer = deepcopy(FAKE_CUSTOMER_II)

        user = get_user_model().objects.create_user(username="testuser", email="testuser@gmail.com")
        Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER_II["id"], currency="usd")

        customer = Customer.sync_from_stripe_data(fake_customer)

        self.assertEqual(FAKE_CUSTOMER_II["default_source"]["id"], customer.default_source.stripe_id)
        self.assertEqual(1, customer.sources.count())

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

        customer_retrieve_mock.assert_called_with(id=self.customer.stripe_id, api_key=settings.STRIPE_SECRET_KEY,
                                                  expand=['default_source'])
        self.assertEquals(2, customer_retrieve_mock.call_count)

    @patch("stripe.Customer.retrieve")
    def test_customer_delete_raises_unexpected_exception(self, customer_retrieve_mock):
        customer_retrieve_mock.side_effect = InvalidRequestError("Unexpected Exception", "blah")

        with self.assertRaisesMessage(InvalidRequestError, "Unexpected Exception"):
            self.customer.purge()

        customer_retrieve_mock.assert_called_once_with(id=self.customer.stripe_id, api_key=settings.STRIPE_SECRET_KEY,
                                                       expand=['default_source'])

    def test_can_charge(self):
        self.assertTrue(self.customer.can_charge())

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_add_card_set_default_true(self, customer_retrieve_mock):
        self.customer.add_card(FAKE_CARD["id"])
        self.customer.add_card(FAKE_CARD_V["id"])

        self.assertEqual(2, Card.objects.count())
        self.assertEqual(FAKE_CARD_V["id"], self.customer.default_source.stripe_id)

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_add_card_set_default_false(self, customer_retrieve_mock):
        self.customer.add_card(FAKE_CARD["id"], set_default=False)
        self.customer.add_card(FAKE_CARD_V["id"], set_default=False)

        self.assertEqual(2, Card.objects.count())
        self.assertEqual(FAKE_CARD["id"], self.customer.default_source.stripe_id)

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_add_card_set_default_false_with_single_card_still_becomes_default(self, customer_retrieve_mock):
        self.customer.add_card(FAKE_CARD["id"], set_default=False)

        self.assertEqual(1, Card.objects.count())
        self.assertEqual(FAKE_CARD["id"], self.customer.default_source.stripe_id)

    @patch("stripe.Customer.retrieve")
    def test_cannot_charge(self, customer_retrieve_fake):
        self.customer.delete()
        self.assertFalse(self.customer.can_charge())

    def test_charge_accepts_only_decimals(self):
        with self.assertRaises(ValueError):
            self.customer.charge(10)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    def test_refund_charge(self, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_no_invoice = deepcopy(FAKE_CHARGE)
        fake_charge_no_invoice.update({"invoice": None})

        charge_retrieve_mock.return_value = fake_charge_no_invoice

        charge, created = Charge._get_or_create_from_stripe_object(fake_charge_no_invoice)
        self.assertTrue(created)

        charge.refund()

        refunded_charge, created2 = Charge._get_or_create_from_stripe_object(fake_charge_no_invoice)
        self.assertFalse(created2)

        self.assertEquals(refunded_charge.refunded, True)
        self.assertEquals(refunded_charge.amount_refunded, decimal.Decimal("22.00"))

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    def test_refund_charge_object_returned(self, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_no_invoice = deepcopy(FAKE_CHARGE)
        fake_charge_no_invoice.update({"invoice": None})

        charge_retrieve_mock.return_value = fake_charge_no_invoice

        charge, created = Charge._get_or_create_from_stripe_object(fake_charge_no_invoice)
        self.assertTrue(created)

        refunded_charge = charge.refund()
        self.assertEquals(refunded_charge.refunded, True)
        self.assertEquals(refunded_charge.amount_refunded, decimal.Decimal("22.00"))

    def test_calculate_refund_amount_full_refund(self):
        charge = Charge(
            stripe_id="ch_111111",
            customer=self.customer,
            amount=decimal.Decimal("500.00")
        )
        self.assertEquals(charge._calculate_refund_amount(), 50000)

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

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    @patch("stripe.Invoice.retrieve")
    def test_charge_doesnt_require_invoice(self, invoice_retrieve_mock, charge_create_mock, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": FAKE_INVOICE["id"], "amount": FAKE_INVOICE["amount_due"]})
        fake_invoice_copy = deepcopy(FAKE_INVOICE)

        charge_create_mock.return_value = fake_charge_copy
        charge_retrieve_mock.return_value = fake_charge_copy
        invoice_retrieve_mock.return_value = fake_invoice_copy

        try:
            self.customer.charge(amount=decimal.Decimal("20.00"))
        except Invoice.DoesNotExist:
            self.fail(msg="Stripe Charge shouldn't throw Invoice DoesNotExist.")

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
            destination=FAKE_ACCOUNT["id"],
        )

        _, kwargs = charge_create_mock.call_args
        self.assertEquals(kwargs["capture"], True)
        self.assertEquals(kwargs["destination"], FAKE_ACCOUNT["id"])

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

    @patch("djstripe.models.djstripe_settings.trial_period_for_subscriber_callback", return_value=7)
    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER_II))
    def test_create_trial_callback_without_default_plan(self, customer_create_mock, callback_mock):
        user = get_user_model().objects.create_user(username="test", email="test@gmail.com")
        Customer.create(user)

        customer_create_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, email=user.email)
        callback_mock.assert_called_once_with(user)

    @patch("djstripe.models.Customer.subscribe")
    @patch("djstripe.models.djstripe_settings.DEFAULT_PLAN")
    @patch("djstripe.models.djstripe_settings.trial_period_for_subscriber_callback", return_value=7)
    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER_II))
    def test_create_default_plan(self, customer_create_mock, callback_mock, default_plan_fake, subscribe_mock):
        user = get_user_model().objects.create_user(username="test", email="test@gmail.com")
        Customer.create(user)

        customer_create_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, email=user.email)
        callback_mock.assert_called_once_with(user)

        self.assertTrue(subscribe_mock.called)
        self.assertTrue(1, subscribe_mock.call_count)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    @patch("stripe.Invoice.list", return_value=StripeList(data=[deepcopy(FAKE_INVOICE), deepcopy(FAKE_INVOICE_III)]))
    @patch("djstripe.models.Invoice.retry", autospec=True)
    def test_retry_unpaid_invoices(self, invoice_retry_mock, invoice_list_mock,
                                   charge_retrieve_mock, customer_retrieve_mock,
                                   subscription_retrive_mock, default_account_mock):
        default_account_mock.return_value = self.account

        self.customer.retry_unpaid_invoices()

        invoice = Invoice.objects.get(stripe_id=FAKE_INVOICE_III["id"])
        invoice_retry_mock.assert_called_once_with(invoice)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    @patch("stripe.Invoice.list", return_value=StripeList(data=[deepcopy(FAKE_INVOICE)]))
    @patch("djstripe.models.Invoice.retry", autospec=True)
    def test_retry_unpaid_invoices_none_unpaid(self, invoice_retry_mock, invoice_list_mock,
                                               charge_retrieve_mock, customer_retrieve_mock,
                                               subscription_retrive_mock, default_account_mock):
        default_account_mock.return_value = self.account

        self.customer.retry_unpaid_invoices()

        self.assertFalse(invoice_retry_mock.called)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    @patch("stripe.Invoice.list", return_value=StripeList(data=[deepcopy(FAKE_INVOICE_III)]))
    @patch("djstripe.models.Invoice.retry", autospec=True)
    def test_retry_unpaid_invoices_expected_exception(self, invoice_retry_mock, invoice_list_mock,
                                                      charge_retrieve_mock, customer_retrieve_mock,
                                                      subscription_retrive_mock, default_account_mock):
        default_account_mock.return_value = self.account
        invoice_retry_mock.side_effect = InvalidRequestError("Invoice is already paid", "blah")

        try:
            self.customer.retry_unpaid_invoices()
        except:
            self.fail("Exception was unexpectedly raised.")

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE))
    @patch("stripe.Invoice.list", return_value=StripeList(data=[deepcopy(FAKE_INVOICE_III)]))
    @patch("djstripe.models.Invoice.retry", autospec=True)
    def test_retry_unpaid_invoices_unexpected_exception(self, invoice_retry_mock, invoice_list_mock,
                                                        charge_retrieve_mock, customer_retrieve_mock,
                                                        subscription_retrive_mock, default_account_mock):
        default_account_mock.return_value = self.account
        invoice_retry_mock.side_effect = InvalidRequestError("This should fail!", "blah")

        with self.assertRaisesMessage(InvalidRequestError, "This should fail!"):
            self.customer.retry_unpaid_invoices()

    @patch("stripe.Invoice.create")
    def test_send_invoice_success(self, invoice_create_mock):
        return_status = self.customer.send_invoice()
        self.assertTrue(return_status)

        invoice_create_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, customer=self.customer.stripe_id)

    @patch("stripe.Invoice.create")
    def test_send_invoice_failure(self, invoice_create_mock):
        invoice_create_mock.side_effect = InvalidRequestError("Invoice creation failed.", "blah")

        return_status = self.customer.send_invoice()
        self.assertFalse(return_status)

        invoice_create_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, customer=self.customer.stripe_id)

    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("stripe.Invoice.list", return_value=StripeList(data=[deepcopy(FAKE_INVOICE), deepcopy(FAKE_INVOICE_III)]))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_sync_invoices(self, customer_retrieve_mock, invoice_list_mock, invoice_sync_mock):
        self.customer._sync_invoices()
        self.assertEqual(2, invoice_sync_mock.call_count)

    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("stripe.Invoice.list", return_value=StripeList(data=[]))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_sync_invoices_none(self, customer_retrieve_mock, invoice_list_mock, invoice_sync_mock):
        self.customer._sync_invoices()
        self.assertEqual(0, invoice_sync_mock.call_count)

    @patch("djstripe.models.Charge.sync_from_stripe_data")
    @patch("stripe.Charge.list", return_value=StripeList(data=[deepcopy(FAKE_CHARGE)]))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_sync_charges(self, customer_retrieve_mock, charge_list_mock, charge_sync_mock):
        self.customer._sync_charges()
        self.assertEqual(1, charge_sync_mock.call_count)

    @patch("djstripe.models.Charge.sync_from_stripe_data")
    @patch("stripe.Charge.list", return_value=StripeList(data=[]))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_sync_charges_none(self, customer_retrieve_mock, charge_list_mock, charge_sync_mock):
        self.customer._sync_charges()
        self.assertEqual(0, charge_sync_mock.call_count)

    @patch("djstripe.models.Subscription.sync_from_stripe_data")
    @patch("stripe.Subscription.list", return_value=StripeList(data=[deepcopy(FAKE_SUBSCRIPTION), deepcopy(FAKE_SUBSCRIPTION_II)]))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_sync_subscriptions(self, customer_retrieve_mock, subscription_list_mock, subscription_sync_mock):
        self.customer._sync_subscriptions()
        self.assertEqual(2, subscription_sync_mock.call_count)

    @patch("djstripe.models.Subscription.sync_from_stripe_data")
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

    @patch("djstripe.models.Customer.send_invoice")
    @patch("stripe.Subscription.create", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_subscribe_charge_immediately(self, customer_retrieve_mock, subscription_create_mock, send_invoice_mock):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        self.customer.subscribe(plan=plan, charge_immediately=True)
        self.assertTrue(send_invoice_mock.called)

    @patch("djstripe.models.Customer.send_invoice")
    @patch("stripe.Subscription.create", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_subscribe_plan_string(self, customer_retrieve_mock, subscription_create_mock, send_invoice_mock):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        self.customer.subscribe(plan=plan.stripe_id, charge_immediately=True)
        self.assertTrue(send_invoice_mock.called)

    @patch("stripe.Subscription.create")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_subscription_shortcut_with_multiple_subscriptions(self, customer_retrieve_mock, subscription_create_mock):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        subscription_fake_duplicate = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake_duplicate["id"] = "sub_6lsC8pt7IcF8jd"

        subscription_create_mock.side_effect = [deepcopy(FAKE_SUBSCRIPTION), subscription_fake_duplicate]

        self.customer.subscribe(plan=plan, charge_immediately=False)
        self.customer.subscribe(plan=plan, charge_immediately=False)

        self.assertEqual(2, self.customer.subscriptions.count())

        with self.assertRaises(MultipleSubscriptionException):
            self.customer.subscription

    @patch("stripe.Subscription.create")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_has_active_subscription_with_unspecified_plan_with_multiple_subscriptions(self, customer_retrieve_mock, subscription_create_mock):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["current_period_end"] = datetime_to_unix(timezone.now() + timezone.timedelta(days=7))

        subscription_fake_duplicate = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake_duplicate["current_period_end"] = datetime_to_unix(timezone.now() + timezone.timedelta(days=7))
        subscription_fake_duplicate["id"] = "sub_6lsC8pt7IcF8jd"

        subscription_create_mock.side_effect = [subscription_fake, subscription_fake_duplicate]

        self.customer.subscribe(plan=plan, charge_immediately=False)
        self.customer.subscribe(plan=plan, charge_immediately=False)

        self.assertEqual(2, self.customer.subscriptions.count())

        with self.assertRaises(TypeError):
            self.customer.has_active_subscription()

    @patch("stripe.Subscription.create")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_has_active_subscription_with_plan(self, customer_retrieve_mock, subscription_create_mock):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["current_period_end"] = datetime_to_unix(timezone.now() + timezone.timedelta(days=7))

        subscription_create_mock.return_value = subscription_fake

        self.customer.subscribe(plan=plan, charge_immediately=False)

        self.customer.has_active_subscription(plan=plan)

    @patch("stripe.Subscription.create")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_has_active_subscription_with_plan_string(self, customer_retrieve_mock, subscription_create_mock):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["current_period_end"] = datetime_to_unix(timezone.now() + timezone.timedelta(days=7))

        subscription_create_mock.return_value = subscription_fake

        self.customer.subscribe(plan=plan, charge_immediately=False)

        self.customer.has_active_subscription(plan=plan.stripe_id)

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

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Invoice.upcoming", return_value=deepcopy(FAKE_UPCOMING_INVOICE))
    def test_upcoming_invoice(self, invoice_upcoming_mock, subscription_retrieve_mock, plan_retrieve_mock):
        invoice = self.customer.upcoming_invoice()
        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.stripe_id)
        self.assertIsNone(invoice.save())

        subscription_retrieve_mock.assert_called_once_with(api_key=ANY, expand=ANY, id=FAKE_SUBSCRIPTION["id"])
        plan_retrieve_mock.assert_not_called()

        items = invoice.invoiceitems.all()
        self.assertEquals(1, len(items))
        self.assertEquals(FAKE_SUBSCRIPTION["id"], items[0].stripe_id)

        self.assertIsNotNone(invoice.plan)
        self.assertEquals(FAKE_PLAN["id"], invoice.plan.stripe_id)

        invoice._invoiceitems = []
        items = invoice.invoiceitems.all()
        self.assertEquals(0, len(items))
        self.assertIsNotNone(invoice.plan)
