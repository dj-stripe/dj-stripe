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

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from mock import patch, PropertyMock, MagicMock
from stripe.error import InvalidRequestError

from djstripe.models import Account, Customer, Charge, Subscription, Invoice

from . import FAKE_CHARGE, FAKE_CUSTOMER, FAKE_ACCOUNT, FAKE_INVOICE, FAKE_INVOICE_II, FAKE_INVOICE_III, DataList


class TestCustomer(TestCase):
    fake_current_subscription = Subscription(plan="test_plan",
                                             quantity=1,
                                             start=timezone.now(),
                                             amount=decimal.Decimal(25.00))

    fake_current_subscription_cancelled_in_stripe = Subscription(plan="test_plan",
                                                                 quantity=1,
                                                                 start=timezone.now(),
                                                                 amount=decimal.Decimal(25.00),
                                                                 status=Subscription.STATUS_ACTIVE)

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="patrick", email="patrick@gmail.com")
        self.customer = Customer.objects.create(
            subscriber=self.user,
            stripe_id="cus_6lsBvm5rJ0zyHc",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )

        self.account = Account.objects.create()

    def test_tostring(self):
        self.assertEquals("<patrick, email=patrick@gmail.com, stripe_id=cus_6lsBvm5rJ0zyHc>", str(self.customer))

    @patch("stripe.Customer.retrieve")
    def test_customer_purge_leaves_customer_record(self, customer_retrieve_fake):
        self.customer.purge()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.card_fingerprint == "")
        self.assertTrue(customer.card_last_4 == "")
        self.assertTrue(customer.card_kind == "")
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    @patch("stripe.Customer.retrieve")
    def test_customer_delete_same_as_purge(self, customer_retrieve_fake):
        self.customer.delete()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.card_fingerprint == "")
        self.assertTrue(customer.card_last_4 == "")
        self.assertTrue(customer.card_kind == "")
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    @patch("stripe.Customer.retrieve")
    def test_customer_purge_raises_customer_exception(self, customer_retrieve_mock):
        customer_retrieve_mock.side_effect = InvalidRequestError("No such customer:", "blah")

        self.customer.purge()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.card_fingerprint == "")
        self.assertTrue(customer.card_last_4 == "")
        self.assertTrue(customer.card_kind == "")
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

        customer_retrieve_mock.assert_called_once_with(id=self.customer.stripe_id, api_key=settings.STRIPE_SECRET_KEY, expand=None)

    @patch("stripe.Customer.retrieve")
    def test_customer_delete_raises_unexpected_exception(self, customer_retrieve_mock):
        customer_retrieve_mock.side_effect = InvalidRequestError("Unexpected Exception", "blah")

        with self.assertRaisesMessage(InvalidRequestError, "Unexpected Exception"):
            self.customer.purge()

        customer_retrieve_mock.assert_called_once_with(id=self.customer.stripe_id, api_key=settings.STRIPE_SECRET_KEY, expand=None)

    def test_can_charge(self):
        self.assertTrue(self.customer.can_charge())

    @patch("stripe.Customer.retrieve")
    def test_cannot_charge(self, customer_retrieve_fake):
        self.customer.delete()
        self.assertFalse(self.customer.can_charge())

    def test_charge_accepts_only_decimals(self):
        with self.assertRaises(ValueError):
            self.customer.charge(10)

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    def test_record_charge(self, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": None})

        charge_retrieve_mock.return_value = fake_charge_copy

        recorded_charge = self.customer.record_charge(fake_charge_copy["id"])
        self.assertEquals(Charge.objects.get(stripe_id=fake_charge_copy["id"]), recorded_charge)
        self.assertEquals(recorded_charge.paid, True)
        self.assertEquals(recorded_charge.disputed, False)
        self.assertEquals(recorded_charge.refunded, False)
        self.assertEquals(recorded_charge.amount_refunded, 0)

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
        fake_charge_copy.update({"invoice": "in_16YHls2eZvKYlo2CwwH968Mc", "amount": 2000})
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
            destination=PropertyMock(stripe_id=FAKE_ACCOUNT["id"]),
        )

        _, kwargs = charge_create_mock.call_args
        self.assertEquals(kwargs["capture"], True)
        self.assertEquals(kwargs["destination"], FAKE_ACCOUNT["id"])

    @patch("djstripe.models.djstripe_settings.trial_period_for_subscriber_callback", return_value="donkey")
    @patch("stripe.Customer.create", return_value=PropertyMock(id="cus_xxx1234567890"))
    def test_create_trial_callback(self, customer_create_mock, callback_mock):
        user = get_user_model().objects.create_user(username="test", email="test@gmail.com")
        Customer.create(user)

        customer_create_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, email=user.email)
        callback_mock.assert_called_once_with(user)

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

    # TODO: Update
    @patch("djstripe.models.Customer.api_retrieve")
    def test_update_card(self, api_retrieve_mock):
        api_retrieve_mock.return_value = PropertyMock(
            active_card=PropertyMock(
                fingerprint="test_fingerprint",
                last4="1234",
                type="test_type",
                exp_month=12,
                exp_year=2020
            )
        )

        self.customer.update_card("test")

    # TODO: Update for removal
    @patch("djstripe.models.Customer.api_retrieve", return_value=PropertyMock(deleted=False))
    def test_sync_non_delted_customer(self, customer_retrieve_mock):
        self.customer._sync()

    @patch("djstripe.models.Customer.invoices", new_callable=PropertyMock,
           return_value=PropertyMock(name="filter", filter=MagicMock(return_value=[MagicMock(name="inv", retry=MagicMock(name="retry", return_value="test"))])))
    @patch("djstripe.models.Customer._sync_invoices")
    def test_retry_unpaid_invoices(self, _sync_invoices_mock, invoices_mock):
        self.customer.retry_unpaid_invoices()

        _sync_invoices_mock.assert_called_once_with()
        # TODO: Figure out how to assert on filter and retry mocks

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

    @patch("djstripe.models.Customer.invoices", new_callable=PropertyMock,
       return_value=PropertyMock(name="filter", filter=MagicMock(return_value=[MagicMock(name="inv", retry=MagicMock(name="retry",
                                                                                                                     return_value="test",
                                                                                                                     side_effect=InvalidRequestError("This should fail!", "blah")))])))
    @patch("djstripe.models.Customer._sync_invoices")
    def test_retry_unpaid_invoices_unexpected_exception(self, _sync_invoices_mock, invoices_mock):
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

    @patch("djstripe.models.Customer.api_retrieve",
           return_value=PropertyMock(deleted=True))
    def test_sync_deleted_in_stripe(self, api_retrieve_mock):
        self.customer._sync()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.card_fingerprint == "")
        self.assertTrue(customer.card_last_4 == "")
        self.assertTrue(customer.card_kind == "")
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("djstripe.models.Customer.api_retrieve", return_value=FAKE_CUSTOMER)
    def test_sync_invoices(self, api_retrieve_mock, sync_from_stripe_data_mock):
        self.customer._sync_invoices()

        sync_from_stripe_data_mock.assert_any_call(FAKE_INVOICE, send_receipt=False)
        sync_from_stripe_data_mock.assert_any_call(FAKE_INVOICE_II, send_receipt=False)
        sync_from_stripe_data_mock.assert_any_call(FAKE_INVOICE_III, send_receipt=False)

        self.assertEqual(3, sync_from_stripe_data_mock.call_count)

    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("tests.FAKE_CUSTOMER.invoices", return_value=DataList(data=[]))
    @patch("djstripe.models.Customer.api_retrieve")
    def test_sync_invoices_none(self, api_retrieve_mock, customer_invoice_retrieve_mock, sync_from_stripe_data_mock):
        self.customer._sync_invoices()

        self.assertFalse(sync_from_stripe_data_mock.called)

    @patch("djstripe.models.Customer.record_charge")
    @patch("djstripe.models.Customer.api_retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_sync_charges(self, api_retrieve_mock, record_charge_mock):
        self.customer._sync_charges()

        record_charge_mock.assert_any_call(FAKE_CHARGE["id"])

        self.assertEqual(1, record_charge_mock.call_count)

    @patch("djstripe.models.Customer.record_charge")
    @patch("djstripe.models.Customer.api_retrieve",
           return_value=PropertyMock(charges=MagicMock(return_value=PropertyMock(data=[]))))
    def test_sync_charges_none(self, api_retrieve_mock, record_charge_mock):
        self.customer._sync_charges()

        self.assertFalse(record_charge_mock.called)

    @patch("djstripe.models.Customer.api_retrieve", return_value=PropertyMock(subscription=None))
    def test_sync_current_subscription_no_stripe_subscription(self, api_retrieve_mock):
        self.assertEqual(None, self.customer._sync_current_subscription())

    @patch("djstripe.models.djstripe_settings.plan_from_stripe_id", return_value="test_plan")
    @patch("djstripe.models.convert_tstamp", return_value=timezone.make_aware(datetime.datetime(2015, 6, 19)))
    @patch("djstripe.models.Customer.current_subscription", new_callable=PropertyMock, return_value=fake_current_subscription)
    @patch("djstripe.models.Customer.api_retrieve", return_value=PropertyMock(subscription=PropertyMock(plan=PropertyMock(id="fish", amount=5000),
                                                                              quantity=5,
                                                                              trial_start=False,
                                                                              trial_end=False,
                                                                              cancel_at_period_end=False,
                                                                              status="tree")))
    def test_sync_current_subscription_update_no_trial(self, api_retrieve_mock, customer_subscription_mock, convert_tstamp_fake, plan_getter_mock):
        tz_test_time = timezone.make_aware(datetime.datetime(2015, 6, 19))

        self.customer._sync_current_subscription()

        plan_getter_mock.assert_called_with("fish")

        self.assertEqual("test_plan", self.fake_current_subscription.plan)
        self.assertEqual(decimal.Decimal("50.00"), self.fake_current_subscription.amount)
        self.assertEqual("tree", self.fake_current_subscription.status)
        self.assertEqual(5, self.fake_current_subscription.quantity)
        self.assertEqual(False, self.fake_current_subscription.cancel_at_period_end)
        self.assertEqual(tz_test_time, self.fake_current_subscription.canceled_at)
        self.assertEqual(tz_test_time, self.fake_current_subscription.start)
        self.assertEqual(tz_test_time, self.fake_current_subscription.current_period_start)
        self.assertEqual(tz_test_time, self.fake_current_subscription.current_period_end)
        self.assertEqual(None, self.fake_current_subscription.trial_start)
        self.assertEqual(None, self.fake_current_subscription.trial_end)

    @patch("djstripe.models.Customer.current_subscription", new_callable=PropertyMock, return_value=fake_current_subscription_cancelled_in_stripe)
    @patch("djstripe.models.Customer.api_retrieve", return_value=PropertyMock(subscription=None))
    def test_sync_current_subscription_subscription_cancelled_from_Stripe(self, api_retrieve_mock, customer_subscription_mock):
        self.assertEqual(Subscription.STATUS_CANCELLED, self.customer._sync_current_subscription().status)

    @patch("djstripe.models.Customer.send_invoice")
    @patch("djstripe.models.Customer._sync_current_subscription")
    @patch("tests.FAKE_CUSTOMER.update_subscription")
    @patch("djstripe.models.Customer.api_retrieve", return_value=FAKE_CUSTOMER)
    def test_subscribe_trial_plan(self, api_retrieve_mock, update_subscription_mock, _sync_subscription_mock, send_invoice_mock):
        trial_days = 7  # From settings

        self.customer.subscribe(plan="test_trial")
        _sync_subscription_mock.assert_called_once_with()
        send_invoice_mock.assert_called_once_with()

        _, call_kwargs = update_subscription_mock.call_args

        self.assertIn("trial_end", call_kwargs)
        self.assertLessEqual(call_kwargs["trial_end"], timezone.now() + datetime.timedelta(days=trial_days))

    @patch("djstripe.models.Customer.send_invoice")
    @patch("djstripe.models.Customer._sync_current_subscription")
    @patch("tests.FAKE_CUSTOMER.update_subscription")
    @patch("djstripe.models.Customer.api_retrieve", return_value=FAKE_CUSTOMER)
    def test_subscribe_trial_days_kwarg(self, api_retrieve_mock, update_subscription_mock, _sync_subscription_mock, send_invoice_mock):
        trial_days = 9

        self.customer.subscribe(plan="test", trial_days=trial_days)
        _sync_subscription_mock.assert_called_once_with()
        send_invoice_mock.assert_called_once_with()

        _, call_kwargs = update_subscription_mock.call_args

        self.assertIn("trial_end", call_kwargs)
        self.assertLessEqual(call_kwargs["trial_end"], timezone.now() + datetime.timedelta(days=trial_days))

    @patch("djstripe.models.Customer.send_invoice")
    @patch("djstripe.models.Customer._sync_current_subscription")
    @patch("djstripe.models.Customer.current_subscription", new_callable=PropertyMock, return_value=fake_current_subscription)
    @patch("djstripe.models.Customer.api_retrieve", return_value=PropertyMock())
    def test_subscribe_not_charge_immediately(self, api_retrieve_mock, customer_subscription_mock, _sync_subscription_mock, send_invoice_mock):
        self.customer.subscribe(plan="test", charge_immediately=False)
        _sync_subscription_mock.assert_called_once_with()
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

    @patch("stripe.InvoiceItem.create")
    def test_add_invoice_item(self, invoice_item_create_mock):
        self.customer.add_invoice_item(amount=decimal.Decimal("50.00"), currency="eur", invoice_id=77, description="test")

        invoice_item_create_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, amount=5000, currency="eur", invoice=77, description="test", customer=self.customer.stripe_id)

    def test_add_invoice_item_bad_decimal(self):
        with self.assertRaisesMessage(ValueError, "You must supply a decimal value representing dollars."):
            self.customer.add_invoice_item(amount=5000)
