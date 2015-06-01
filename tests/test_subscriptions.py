import calendar
import copy
import datetime
import decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from mock import patch, PropertyMock

from stripe import api_key, InvalidRequestError
from stripe.resource import convert_to_stripe_object
from stripe.version import VERSION as STRIPE_VERSION

from djstripe.exceptions import SubscriptionCancellationFailure
from djstripe.models import convert_tstamp, Customer, CurrentSubscription
from djstripe.settings import PAYMENTS_PLANS


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
    CurrentSubscription.objects.create(
        customer=customer,
        plan=plan,
        quantity=1,
        start=convert_tstamp(1395527780),
        amount=decimal.Decimal("100.00" if plan == "basic" else "1000.00"),
        status="trialing"
    )


def version_tuple(v):
    return tuple(map(int, (v.split("."))))


def safe_convert_to_stripe_object(resp, api_key):
    if version_tuple(STRIPE_VERSION) > version_tuple("1.20.2"):
        return convert_to_stripe_object(resp, api_key, account="acct_test")
    else:
        return convert_to_stripe_object(resp, api_key)


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
        StripeCustomerMock.side_effect = [safe_convert_to_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB, api_key),
                                          safe_convert_to_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC, api_key)]
        self.assertEqual(self.customer.has_active_subscription(), False)
        self.customer.subscribe("basic", charge_immediately=False)
        self.assertEqual(self.customer.has_active_subscription(), True)
        sub = self.customer.current_subscription
        self.assertEqual(sub.quantity, 1)
        self.assertEqual(sub.amount, decimal.Decimal("100.00"))

    @patch("stripe.resource.Customer.update_subscription")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_upgrade(self, StripeCustomerMock, UpdateSubscriptionMock):
        StripeCustomerMock.side_effect = [safe_convert_to_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC, api_key),
                                          safe_convert_to_stripe_object(DUMMY_CUSTOMER_WITH_SUB_GOLD, api_key)]
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
        StripeCustomerMock.return_value = safe_convert_to_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB, api_key)
        CancelSubscriptionMock.side_effect = InvalidRequestError("No active subscriptions for customer: cus_xxxxxxxxxxxxxx", None)
        create_subscription(self.customer)
        self.assertEqual(self.customer.has_active_subscription(), True)
        self.assertEqual(self.customer.current_subscription.status, "trialing")
        with self.assertRaises(SubscriptionCancellationFailure):
            self.customer.cancel_subscription()

    @patch("stripe.resource.Customer.cancel_subscription")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_cancel_with_stripe_sub(self, StripeCustomerMock, CancelSubscriptionMock):
        StripeCustomerMock.return_value = safe_convert_to_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC, api_key)
        CancelSubscriptionMock.return_value = safe_convert_to_stripe_object(DUMMY_SUB_BASIC_CANCELED, api_key)
        create_subscription(self.customer)
        self.assertEqual(self.customer.current_subscription.status, "trialing")
        self.customer.cancel_subscription(at_period_end=False)
        self.assertEqual(self.customer.has_active_subscription(), False)
        self.assertEqual(self.customer.current_subscription.status, "canceled")
        self.assertEqual(self.customer.current_subscription.ended_at, None)
        self.assertEqual(self.customer.current_subscription.canceled_at, convert_tstamp(CANCELED_TIME))

    @patch("stripe.resource.Customer.update_subscription")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_update_quantity(self, StripeCustomerMock, UpdateSubscriptionMock):
        dummy_customer = copy.deepcopy(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        dummy_customer["subscription"]["quantity"] = 2
        StripeCustomerMock.side_effect = [safe_convert_to_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC, api_key),
                                          safe_convert_to_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC, api_key),
                                          safe_convert_to_stripe_object(dummy_customer, api_key)]
        create_subscription(self.customer)
        self.customer.update_plan_quantity(2, charge_immediately=False)
        self.assertEqual(self.customer.current_subscription.quantity, 2)
