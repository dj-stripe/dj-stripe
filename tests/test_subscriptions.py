import calendar
import copy
import datetime
import decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from mock import patch, PropertyMock
from stripe import InvalidRequestError

from djstripe.exceptions import SubscriptionCancellationFailure, SubscriptionUpdateFailure
from djstripe.models import convert_tstamp, Customer, CurrentSubscription
from djstripe.settings import PAYMENTS_PLANS
from tests import convert_to_fake_stripe_object


def timestamp(year, month, day, hour, minute=0, second=0):
    dt = datetime.datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    return calendar.timegm(dt.timetuple())


CREATE_TIME = timestamp(2014, 4, 1, 11)
START_TIME = timestamp(2014, 4, 1, 12)
END_TIME = timestamp(2014, 4, 11, 12)
CANCELED_TIME = timestamp(2014, 4, 6, 12)

BASIC_PLAN = {
    "stripe_plan_id": "basic_id",
    "name": "Basic Plan",
    "description": "Basic Plan (monthly)",
    "price": 10000,
    "currency": "usd",
    "interval": "month"
}

GOLD_PLAN = {
    "stripe_plan_id": "gold_id",
    "name": "Gold Plan",
    "description": "Gold Plan (annual)",
    "price": 100000,
    "currency": "usd",
    "interval": "year"
}

DUMMY_CUSTOMER_WITHOUT_SUB = {
    "object": "customer",
    "created": CREATE_TIME,
    "id": "cus_xxxxxxxxxxxxxx",
    "subscription": None,
    "cards": {
        "object": "list",
        "count": 0,
        "data": []
    },
    "default_card": None
}

DUMMY_SUB_BASIC = {
    "plan": "basic_id",
    "object": "subscription",
    "start": START_TIME,
    "status": "trialing",
    "customer": "cus_xxxxxxxxxxxxxx",
    "cancel_at_period_end": False,
    "current_period_start": START_TIME,
    "current_period_end": END_TIME,
    "ended_at": None,
    "trial_start": START_TIME,
    "trial_end": END_TIME,
    "canceled_at": None,
    "quantity": 1
}

DUMMY_SUB_BASIC_CANCELED = {
    "plan": "basic_id",
    "object": "subscription",
    "start": START_TIME,
    "status": "canceled",
    "customer": "cus_xxxxxxxxxxxxxx",
    "cancel_at_period_end": False,
    "current_period_start": START_TIME,
    "current_period_end": END_TIME,
    "ended_at": CANCELED_TIME,
    "trial_start": START_TIME,
    "trial_end": END_TIME,
    "canceled_at": CANCELED_TIME,
    "quantity": 1
}

DUMMY_SUB_GOLD = {
    "plan": "gold_id",
    "object": "subscription",
    "start": START_TIME,
    "status": "trialing",
    "customer": "cus_xxxxxxxxxxxxxx",
    "cancel_at_period_end": False,
    "current_period_start": START_TIME,
    "current_period_end": END_TIME,
    "ended_at": None,
    "trial_start": START_TIME,
    "trial_end": END_TIME,
    "canceled_at": None,
    "quantity": 1
}

DUMMY_SUB_BASIC_WITH_PLAN = copy.deepcopy(DUMMY_SUB_BASIC)
DUMMY_SUB_BASIC_WITH_PLAN["plan"] = {"id": "basic_id", "object": "plan", "amount": 10000}
DUMMY_CUSTOMER_WITH_SUB_BASIC = copy.deepcopy(DUMMY_CUSTOMER_WITHOUT_SUB)
DUMMY_CUSTOMER_WITH_SUB_BASIC["subscription"] = DUMMY_SUB_BASIC_WITH_PLAN

DUMMY_SUB_GOLD_WITH_PLAN = copy.deepcopy(DUMMY_SUB_GOLD)
DUMMY_SUB_GOLD_WITH_PLAN["plan"] = {"id": "gold_id", "object": "plan", "amount": 100000}
DUMMY_CUSTOMER_WITH_SUB_GOLD = copy.deepcopy(DUMMY_CUSTOMER_WITHOUT_SUB)
DUMMY_CUSTOMER_WITH_SUB_GOLD["subscription"] = DUMMY_SUB_GOLD_WITH_PLAN


def create_subscription(customer, plan="basic"):
    return CurrentSubscription.objects.create(
        customer=customer,
        plan=plan,
        quantity=1,
        start=convert_tstamp(1395527780),
        amount=decimal.Decimal("100.00" if plan == "basic" else "1000.00"),
        status="trialing"
    )


def version_tuple(v):
    return tuple(map(int, (v.split("."))))


class TestSingleSubscription(TestCase):

    @classmethod
    def setupClass(cls):
        PAYMENTS_PLANS["basic"] = BASIC_PLAN
        PAYMENTS_PLANS["gold"] = GOLD_PLAN

    @classmethod
    def tearDownClass(cls):
        del PAYMENTS_PLANS["basic"]
        del PAYMENTS_PLANS["gold"]

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="chris")
        self.customer = Customer.objects.create(
            subscriber=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )

    def test_current_subscription_does_not_exist(self):
        with self.assertRaises(CurrentSubscription.DoesNotExist):
            self.customer.current_subscription

    @patch("stripe.resource.Customer.update_subscription")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_subscribe(self, StripeCustomerMock, UpdateSubscriptionMock):
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)]
        self.assertEqual(self.customer.has_active_subscription(), False)
        self.customer.subscribe("basic", charge_immediately=False)
        self.assertEqual(self.customer.has_active_subscription(), True)
        sub = self.customer.current_subscription
        self.assertEqual(sub.quantity, 1)
        self.assertEqual(sub.amount, decimal.Decimal("100.00"))

    @patch("stripe.resource.Customer.update_subscription")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_upgrade(self, StripeCustomerMock, UpdateSubscriptionMock):
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_GOLD)]
        create_subscription(self.customer)
        self.assertEqual(self.customer.has_active_subscription(), True)
        self.assertEqual(self.customer.current_subscription.plan, "basic")
        self.customer.subscribe("gold", charge_immediately=False)
        self.assertEqual(self.customer.has_active_subscription(), True)
        sub = self.customer.current_subscription
        self.assertEqual(sub.amount, decimal.Decimal("1000.00"))
        self.assertEqual(sub.plan, "gold")

    def test_cancel_without_sub(self):
        with self.assertRaises(SubscriptionCancellationFailure):
            self.customer.cancel_subscription()

    @patch("stripe.resource.Customer.cancel_subscription", new_callable=PropertyMock)
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_cancel_without_stripe_sub(self, StripeCustomerMock, CancelSubscriptionMock):
        StripeCustomerMock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB)
        CancelSubscriptionMock.side_effect = InvalidRequestError("No active subscriptions for customer: cus_xxxxxxxxxxxxxx", None)
        create_subscription(self.customer)
        self.assertEqual(self.customer.has_active_subscription(), True)
        self.assertEqual(self.customer.current_subscription.status, "trialing")
        with self.assertRaises(SubscriptionCancellationFailure):
            self.customer.cancel_subscription()

    @patch("stripe.resource.Customer.cancel_subscription")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_cancel_with_stripe_sub(self, StripeCustomerMock, CancelSubscriptionMock):
        StripeCustomerMock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        CancelSubscriptionMock.return_value = convert_to_fake_stripe_object(DUMMY_SUB_BASIC_CANCELED)
        create_subscription(self.customer)
        self.assertEqual(self.customer.current_subscription.status, "trialing")
        self.customer.cancel_subscription(at_period_end=False)
        self.assertEqual(self.customer.has_active_subscription(), False)
        self.assertEqual(self.customer.current_subscription.status, "canceled")
        self.assertEqual(self.customer.current_subscription.ended_at, None)
        self.assertEqual(self.customer.current_subscription.canceled_at, convert_tstamp(CANCELED_TIME))

    @patch("stripe.resource.Customer.cancel_subscription")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_cancel_with_stripe_sub_future(self, stripe_customer_mock, cancel_subscription_mock):
        stripe_customer_mock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        cancel_subscription_mock.return_value = convert_to_fake_stripe_object(DUMMY_SUB_BASIC_CANCELED)
        subscription_instance = create_subscription(self.customer)
        subscription_instance.trial_end = timezone.now() + datetime.timedelta(days=5)
        subscription_instance.save()

        self.customer.cancel_subscription(at_period_end=True)
        self.assertEqual(self.customer.has_active_subscription(), False)
        self.assertEqual(self.customer.current_subscription.status, "canceled")

    @patch("stripe.resource.Customer.update_subscription")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_update_quantity(self, StripeCustomerMock, UpdateSubscriptionMock):
        dummy_customer = copy.deepcopy(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        dummy_customer["subscription"]["quantity"] = 2
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(dummy_customer)]
        create_subscription(self.customer)
        self.customer.update_plan_quantity(2, charge_immediately=False)
        self.assertEqual(self.customer.current_subscription.quantity, 2)

    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_update_no_stripe_sub(self, StripeCustomerMock):
        StripeCustomerMock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB)
        create_subscription(self.customer)
        with self.assertRaises(SubscriptionUpdateFailure):
            self.customer.update_plan_quantity(2)

    @patch("stripe.resource.Customer.update_subscription")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_extend(self, StripeCustomerMock, UpdateSubscriptionMock):
        StripeCustomerMock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        subscription_instance = create_subscription(self.customer)
        subscription_instance.current_period_end = timezone.datetime.fromtimestamp(END_TIME, tz=timezone.utc)
        delta = timezone.timedelta(days=30)
        self.customer.current_subscription.extend(delta)
        UpdateSubscriptionMock.assert_called_once_with(prorate=False, trial_end=subscription_instance.current_period_end + delta)

    def test_extend_negative_delta(self):
        delta = timezone.timedelta(days=-30)
        create_subscription(self.customer)
        with self.assertRaises(ValueError):
            self.customer.current_subscription.extend(delta)

    @patch("stripe.resource.Customer.update_subscription")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_extend_with_trial(self, StripeCustomerMock, UpdateSubscriptionMock):
        StripeCustomerMock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        subscription_instance = create_subscription(self.customer)
        subscription_instance.trial_end = timezone.now() + timezone.timedelta(days=5)

        delta = timezone.timedelta(days=30)
        new_trial_end = subscription_instance.trial_end + delta
        self.customer.current_subscription.extend(delta)
        UpdateSubscriptionMock.assert_called_once_with(prorate=False, trial_end=new_trial_end)


class CurrentSubscriptionTest(TestCase):

    def setUp(self):
        self.plan_id = "test"
        self.current_subscription = CurrentSubscription.objects.create(plan=self.plan_id,
                                                                       quantity=1,
                                                                       start=timezone.now(),
                                                                       amount=decimal.Decimal(25.00),
                                                                       status=CurrentSubscription.STATUS_PAST_DUE)

    def test_plan_display(self):
        self.assertEquals(PAYMENTS_PLANS[self.plan_id]["name"], self.current_subscription.plan_display())

    def test_status_display(self):
        self.assertEqual("Past Due", self.current_subscription.status_display())

    def test_is_period_current_no_current_period_end(self):
        self.assertFalse(self.current_subscription.is_period_current())

    def test_is_status_temporarily_current_true(self):
        current_subscription = CurrentSubscription.objects.create(plan=self.plan_id,
                                                                  quantity=1,
                                                                  start=timezone.now(),
                                                                  amount=decimal.Decimal(25.00),
                                                                  status=CurrentSubscription.STATUS_PAST_DUE,
                                                                  canceled_at=timezone.now() + datetime.timedelta(days=5),
                                                                  cancel_at_period_end=True)

        self.assertTrue(current_subscription.is_status_temporarily_current())

    def test_is_status_temporarily_current_false(self):
        self.assertFalse(self.current_subscription.is_status_temporarily_current())
