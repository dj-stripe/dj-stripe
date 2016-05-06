import calendar
from copy import deepcopy
import copy
import datetime
import decimal
from unittest.case import skip

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from mock import patch, PropertyMock
from stripe import InvalidRequestError

from djstripe.exceptions import SubscriptionCancellationFailure, SubscriptionUpdateFailure
from djstripe.models import Customer, Subscription
from djstripe.settings import PAYMENTS_PLANS
from djstripe.utils import convert_tstamp
from tests import convert_to_fake_stripe_object, FAKE_SUBSCRIPTION, FAKE_PLAN, FAKE_CUSTOMER


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
    "livemode": True,
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
    return Subscription.objects.create(
        customer=customer,
        plan=plan,
        quantity=1,
        start=convert_tstamp(1395527780),
        amount=decimal.Decimal("100.00" if plan == "basic" else "1000.00"),
        status="trialing"
    )


def version_tuple(v):
    return tuple(map(int, (v.split("."))))

@skip
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
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        self.customer = Customer.objects.create(subscriber=self.user, stripe_id="cus_xxxxxxxxxxxxxxx", currency="usd")

    def test_current_subscription_does_not_exist(self):
        with self.assertRaises(Subscription.DoesNotExist):
            self.customer.current_subscription

    @patch("stripe.resource.Customer.update_subscription")
    @patch("djstripe.models.Customer.api_retrieve")
    def test_subscribe(self, api_retrieve_mock, UpdateSubscriptionMock):
        api_retrieve_mock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB),
                                         convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)]
        self.assertEqual(self.customer.has_active_subscription(), False)
        self.customer.subscribe("basic", charge_immediately=False)
        self.assertEqual(self.customer.has_active_subscription(), True)
        sub = self.customer.current_subscription
        self.assertEqual(sub.quantity, 1)
        self.assertEqual(sub.amount, decimal.Decimal("100.00"))

    @patch("stripe.resource.Customer.update_subscription")
    @patch("djstripe.models.Customer.api_retrieve")
    def test_upgrade(self, api_retrieve_mock, UpdateSubscriptionMock):
        api_retrieve_mock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                         convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_GOLD)]
        create_subscription(self.customer)
        self.assertEqual(self.customer.has_active_subscription(), True)
        self.assertEqual(self.customer.current_subscription.plan, "basic")
        self.customer.subscribe("gold", charge_immediately=False)
        self.assertEqual(self.customer.has_active_subscription(), True)
        sub = self.customer.current_subscription
        self.assertEqual(sub.amount, decimal.Decimal("1000.00"))
        self.assertEqual(sub.plan, "gold")

    @patch("djstripe.models.Customer.api_retrieve")
    def test_cancel_without_sub(self, api_retrieve_mock):
        with self.assertRaises(SubscriptionCancellationFailure):
            self.customer.cancel_subscription()

    @patch("stripe.resource.Customer.cancel_subscription", new_callable=PropertyMock)
    @patch("djstripe.models.Customer.api_retrieve")
    def test_cancel_without_stripe_sub(self, api_retrieve_mock, CancelSubscriptionMock):
        api_retrieve_mock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB)
        CancelSubscriptionMock.side_effect = InvalidRequestError("No active subscriptions for customer: cus_xxxxxxxxxxxxxx", None)
        create_subscription(self.customer)
        self.assertEqual(self.customer.has_active_subscription(), True)
        self.assertEqual(self.customer.current_subscription.status, "trialing")
        with self.assertRaises(SubscriptionCancellationFailure):
            self.customer.cancel_subscription()

    @patch("stripe.resource.Customer.cancel_subscription")
    @patch("djstripe.models.Customer.api_retrieve")
    def test_cancel_with_stripe_sub(self, api_retrieve_mock, CancelSubscriptionMock):
        api_retrieve_mock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        CancelSubscriptionMock.return_value = convert_to_fake_stripe_object(DUMMY_SUB_BASIC_CANCELED)
        create_subscription(self.customer)
        self.assertEqual(self.customer.current_subscription.status, "trialing")
        self.customer.cancel_subscription(at_period_end=False)
        self.assertEqual(self.customer.has_active_subscription(), False)
        self.assertEqual(self.customer.current_subscription.status, "canceled")
        self.assertEqual(self.customer.current_subscription.ended_at, None)
        self.assertEqual(self.customer.current_subscription.canceled_at, convert_tstamp(CANCELED_TIME))

    @patch("stripe.resource.Customer.cancel_subscription")
    @patch("djstripe.models.Customer.api_retrieve")
    def test_cancel_with_stripe_sub_future(self, api_retrieve_mock, cancel_subscription_mock):
        api_retrieve_mock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        cancel_subscription_mock.return_value = convert_to_fake_stripe_object(DUMMY_SUB_BASIC_CANCELED)
        subscription_instance = create_subscription(self.customer)
        subscription_instance.trial_end = timezone.now() + datetime.timedelta(days=5)
        subscription_instance.save()

        self.customer.cancel_subscription(at_period_end=True)
        self.assertEqual(self.customer.has_active_subscription(), False)
        self.assertEqual(self.customer.current_subscription.status, "canceled")

    @patch("stripe.resource.Customer.update_subscription")
    @patch("djstripe.models.Customer.api_retrieve")
    def test_update_quantity(self, api_retrieve_mock, UpdateSubscriptionMock):
        dummy_customer = copy.deepcopy(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        dummy_customer["subscription"]["quantity"] = 2
        api_retrieve_mock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                         convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                        convert_to_fake_stripe_object(dummy_customer)]
        create_subscription(self.customer)
        self.customer.update_plan_quantity(2, charge_immediately=False)
        self.assertEqual(self.customer.current_subscription.quantity, 2)

    @patch("djstripe.models.Customer.api_retrieve")
    def test_update_no_stripe_sub(self, api_retrieve_mock):
        api_retrieve_mock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB)
        create_subscription(self.customer)
        with self.assertRaises(SubscriptionUpdateFailure):
            self.customer.update_plan_quantity(2)

    @patch("stripe.resource.Customer.update_subscription")
    @patch("djstripe.models.Customer.api_retrieve")
    def test_extend(self, api_retrieve_mock, UpdateSubscriptionMock):
        api_retrieve_mock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)
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
    @patch("djstripe.models.Customer.api_retrieve")
    def test_extend_with_trial(self, api_retrieve_mock, UpdateSubscriptionMock):
        api_retrieve_mock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        subscription_instance = create_subscription(self.customer)
        subscription_instance.trial_end = timezone.now() + timezone.timedelta(days=5)

        delta = timezone.timedelta(days=30)
        new_trial_end = subscription_instance.trial_end + delta
        self.customer.current_subscription.extend(delta)
        UpdateSubscriptionMock.assert_called_once_with(prorate=False, trial_end=new_trial_end)


class SubscriptionTest(TestCase):

    def setUp(self):
        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_str(self, customer_retrieve_mock, plan_retreive_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        self.assertEqual("<current_period_start={current_period_start}, current_period_end={current_period_end}, status={status}, quantity={quantity}, stripe_id={stripe_id}>".format(
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            status=subscription.status,
            quantity=subscription.quantity,
            stripe_id=subscription.stripe_id
        ), str(subscription))

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_is_status_temporarily_current(self, customer_retrieve_mock, plan_retreive_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.status = Subscription.STATUS_CANCELLED
        subscription.canceled_at = timezone.now() + datetime.timedelta(days=7)
        subscription.current_period_end = timezone.now() + datetime.timedelta(days=7)
        subscription.cancel_at_period_end = True
        subscription.save()

        self.assertFalse(subscription.is_status_current())
        self.assertTrue(subscription.is_status_temporarily_current())
        self.assertTrue(subscription.is_valid())

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_is_status_temporarily_current_false(self, customer_retrieve_mock, plan_retreive_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.current_period_end = timezone.now() + datetime.timedelta(days=7)
        subscription.save()

        self.assertTrue(subscription.is_status_current())
        self.assertFalse(subscription.is_status_temporarily_current())
        self.assertTrue(subscription.is_valid())

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_is_status_temporarily_current_false_and_cancelled(self, customer_retrieve_mock, plan_retreive_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.status = Subscription.STATUS_CANCELLED
        subscription.current_period_end = timezone.now() + datetime.timedelta(days=7)
        subscription.save()

        self.assertFalse(subscription.is_status_current())
        self.assertFalse(subscription.is_status_temporarily_current())
        self.assertFalse(subscription.is_valid())
