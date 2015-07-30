import calendar
import copy
import datetime
import decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from mock import patch, PropertyMock, MagicMock

from djstripe.exceptions import SubscriptionApiError, SubscriptionCancellationFailure
from djstripe.models import convert_tstamp, Customer, Subscription
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
    "subscriptions": {
        "object": "list",
        "count": 0,
        "data": []
    },
    "cards": {
        "object": "list",
        "count": 0,
        "data": []
    },
    "default_card": None
}

DUMMY_SUB_BASIC = {
    "id": "sub_yyyyyyyyyyyyyy",
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
    "id": "sub_yyyyyyyyyyyyyy",
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
    "id": "sub_yyyyyyyyyyyyyy",
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
DUMMY_CUSTOMER_WITH_SUB_BASIC["subscriptions"]["count"] = 1
DUMMY_CUSTOMER_WITH_SUB_BASIC["subscriptions"]["data"].append(DUMMY_SUB_BASIC_WITH_PLAN)

DUMMY_SUB_GOLD_WITH_PLAN = copy.deepcopy(DUMMY_SUB_GOLD)
DUMMY_SUB_GOLD_WITH_PLAN["plan"] = {"id": "gold_id", "object": "plan", "amount": 100000}
DUMMY_CUSTOMER_WITH_SUB_GOLD = copy.deepcopy(DUMMY_CUSTOMER_WITHOUT_SUB)
DUMMY_CUSTOMER_WITH_SUB_GOLD["subscriptions"]["count"] = 1
DUMMY_CUSTOMER_WITH_SUB_GOLD["subscriptions"]["data"].append(DUMMY_SUB_GOLD_WITH_PLAN)

DUMMY_CUSTOMER_WITH_BOTH_SUBS = copy.deepcopy(DUMMY_CUSTOMER_WITH_SUB_BASIC)
DUMMY_CUSTOMER_WITH_BOTH_SUBS["subscriptions"]["count"] = 2
DUMMY_CUSTOMER_WITH_BOTH_SUBS["subscriptions"]["data"].append(DUMMY_SUB_GOLD_WITH_PLAN)
DUMMY_CUSTOMER_WITH_BOTH_SUBS["subscriptions"]["data"][1]["id"] = "sub_zzzzzzzzzzzzzz"


def create_subscription(customer, plan="basic"):
    return Subscription.objects.create(
        stripe_id="sub_yyyyyyyyyyyyyy" if plan == "basic" else "sub_zzzzzzzzzzzzzz",
        customer=customer,
        plan=plan,
        quantity=1,
        start=convert_tstamp(1395527780),
        amount=decimal.Decimal("100.00" if plan == "basic" else "1000.00"),
        status="trialing"
    )
    

class TestMultipleSubscriptions(TestCase):

    @classmethod
    def setupClass(cls):
        PAYMENTS_PLANS["basic"] = BASIC_PLAN
        PAYMENTS_PLANS["gold"] = GOLD_PLAN

    @classmethod
    def tearDownClass(cls):
        del PAYMENTS_PLANS["basic"]
        del PAYMENTS_PLANS["gold"]
        
    def setUp(self):
        Customer.allow_multiple_subscriptions = True
        self.user = get_user_model().objects.create_user(username="chris")
        self.customer = Customer.objects.create(
            subscriber=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )

    def tearDown(self):
        Customer.allow_multiple_subscriptions = False

    def test_current_subscription_not_allowed(self):
        with self.assertRaises(SubscriptionApiError):
            self.customer.current_subscription
            
    def test_sync_current_subscription_not_allowed(self):
        with self.assertRaises(SubscriptionApiError):
            self.customer.sync_current_subscription()

    @patch("stripe.resource.ListObject.create")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_subscribe(self, StripeCustomerMock, ListObjectCreateMock):
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_BOTH_SUBS)]
        self.assertEqual(self.customer.subscriptions.count(), 0)
        self.customer.subscribe("basic", charge_immediately=False)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        sub_basic = self.customer.subscriptions.all()[0]
        self.assertEqual(sub_basic.quantity, 1)
        self.assertEqual(sub_basic.amount, decimal.Decimal("100.00"))
        self.customer.subscribe("gold", charge_immediately=False)
        self.assertEqual(self.customer.subscriptions.count(), 2)
        sub_gold = self.customer.subscriptions.get(plan="gold")
        self.assertEqual(sub_gold.quantity, 1)
        self.assertEqual(sub_gold.amount, decimal.Decimal("1000.00"))
        self.assertNotEqual(sub_basic.stripe_id, sub_gold.stripe_id)
        
    @patch("stripe.resource.Subscription.save")
    @patch("stripe.resource.ListObject.create")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_subscribe_with_sub(self, StripeCustomerMock, ListObjectCreateMock, SubscriptionSaveMock):
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)]
        self.customer.subscribe("basic", charge_immediately=False)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        sub_basic = self.customer.subscriptions.all()[0]
        self.customer.subscribe("basic", trial_days=10, charge_immediately=False, subscription=sub_basic)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        SubscriptionSaveMock.assert_called_once_with()
        
    @patch("stripe.resource.Subscription.save")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_upgrade(self, StripeCustomerMock, SubscriptionSaveMock):
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_GOLD)]
        create_subscription(self.customer)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        sub = self.customer.subscriptions.get(plan="basic")
        self.customer.subscribe("gold", charge_immediately=False, subscription=sub)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        sub = self.customer.subscriptions.get(plan="gold")
        self.assertEqual(sub.amount, decimal.Decimal("1000.00"))
        
    def test_cancel_with_no_sub_param(self):
        with self.assertRaises(SubscriptionApiError):
            self.customer.cancel_subscription(at_period_end=False)

    @patch("stripe.resource.Subscription.delete")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_cancel_with_both_subs(self, StripeCustomerMock, SubscriptionDeleteMock):
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_BOTH_SUBS),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_GOLD)]
        SubscriptionDeleteMock.return_value = convert_to_fake_stripe_object(DUMMY_SUB_BASIC_CANCELED)
        create_subscription(self.customer)
        create_subscription(self.customer, "gold")
        sub_basic = self.customer.subscriptions.get(plan="basic")
        self.assertEqual(sub_basic.status, "trialing")
        self.assertEqual(sub_basic.plan, "basic")
        self.customer.cancel_subscription(at_period_end=False, subscription=sub_basic)
        self.assertEqual(self.customer.subscriptions.count(), 2)
        self.assertEqual(sub_basic.status, "canceled")
        self.assertEqual(sub_basic.canceled_at, convert_tstamp(CANCELED_TIME))
        sub_gold = self.customer.subscriptions.get(plan="gold")
        self.assertEqual(sub_gold.status, "trialing")
        # Now, after a synchronise, canceled subs will be removed.
        self.customer.sync_subscriptions()
        self.assertEqual(self.customer.subscriptions.count(), 1)
        with self.assertRaises(Subscription.DoesNotExist):
            self.customer.subscriptions.get(plan="basic")
        
    @patch("stripe.resource.Subscription.delete")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_cancel_with_bad_stripe_sub(self, StripeCustomerMock, SubscriptionDeleteMock):
        StripeCustomerMock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        SubscriptionDeleteMock.return_value = convert_to_fake_stripe_object(DUMMY_SUB_BASIC_CANCELED)
        create_subscription(self.customer)
        self.assertEqual(self.customer.subscriptions.count(), 1)
    
        stripe_subscription = MagicMock()
        p = PropertyMock(return_value="not_sub_id")
        type(stripe_subscription).stripe_id = p
    
        self.customer.cancel_subscription(subscription=stripe_subscription)
    
        self.assertEqual(self.customer.subscriptions.count(), 1)
    
    def test_update_quantity_with_no_sub_param(self):
        with self.assertRaises(SubscriptionApiError):
            self.customer.update_plan_quantity(2)

    @patch("stripe.resource.Subscription.save")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_update_quantity(self, StripeCustomerMock, SubscriptionSaveMock):
        dummy_customer = copy.deepcopy(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        dummy_customer["subscriptions"]["data"][0]["quantity"] = 2
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(dummy_customer)]
        create_subscription(self.customer)
        self.customer.update_plan_quantity(2, charge_immediately=False,
                                           subscription=self.customer.subscriptions.get(plan="basic"))
        self.assertEqual(self.customer.subscriptions.get(plan="basic").quantity, 2)

    @patch("stripe.resource.Subscription.save")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_update_quantity_badsub(self, StripeCustomerMock, SubscriptionSaveMock):
        dummy_customer = copy.deepcopy(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        dummy_customer["subscriptions"]["data"][0]["quantity"] = 2
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(dummy_customer)]
        create_subscription(self.customer)
        stripe_subscription = MagicMock()
        p = PropertyMock(return_value="not_sub_id")
        type(stripe_subscription).stripe_id = p
        self.customer.update_plan_quantity(2, charge_immediately=False,
                                           subscription=stripe_subscription)
        # didnt update anything, stripe_subscription matches nothing attached to this
        # customer
        self.assertEqual(self.customer.subscriptions.get(plan="basic").quantity, 1)
        
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_sync_with_retain_canceled(self, StripeCustomerMock):
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_BOTH_SUBS)]
        Customer.retain_canceled_subscriptions = True
        create_subscription(self.customer)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        self.customer.sync_subscriptions()
        Customer.retain_canceled_subscriptions = False
        self.assertEqual(self.customer.subscriptions.count(), 2)

    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_sync_with_no_subscriptions(self, StripeCustomerMock):
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB)]
        create_subscription(self.customer)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        Customer.retain_canceled_subscriptions = False
        self.customer.sync_subscriptions()
        self.assertEqual(self.customer.subscriptions.count(), 0)


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
        with self.assertRaises(Subscription.DoesNotExist):
            self.customer.current_subscription

    @patch("stripe.resource.ListObject.create")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_subscribe(self, StripeCustomerMock, ListObjectCreateMock):
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)]
        self.assertEqual(self.customer.subscriptions.count(), 0)
        self.assertEqual(self.customer.has_active_subscription(), False)
        self.customer.subscribe("basic", charge_immediately=False)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        self.assertEqual(self.customer.has_active_subscription(), True)
        sub = self.customer.current_subscription
        self.assertEqual(sub.quantity, 1)
        self.assertEqual(sub.amount, decimal.Decimal("100.00"))

    @patch("stripe.resource.Subscription.save")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_upgrade(self, StripeCustomerMock, SubscriptionSaveMock):
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_GOLD),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_GOLD)]
        create_subscription(self.customer)
        self.assertEqual(self.customer.has_active_subscription(), True)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        self.assertEqual(self.customer.current_subscription.plan, "basic")
        self.customer.subscribe("gold", charge_immediately=False)
        self.assertEqual(self.customer.has_active_subscription(), True)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        sub = self.customer.current_subscription
        self.assertEqual(sub.amount, decimal.Decimal("1000.00"))
        self.assertEqual(sub.plan, "gold")
        
    def test_cancel_without_sub(self):
        with self.assertRaises(SubscriptionCancellationFailure):
            self.customer.cancel_subscription()
            
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_cancel_without_stripe_sub(self, StripeCustomerMock):
        StripeCustomerMock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB)
        create_subscription(self.customer)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        self.assertEqual(self.customer.current_subscription.status, "trialing")
        self.customer.cancel_subscription()
        self.assertEqual(self.customer.subscriptions.count(), 1)
        self.assertEqual(self.customer.current_subscription.status, "canceled")
        self.assertEqual(self.customer.current_subscription.ended_at, None)
        self.assertLess(datetime.datetime.now(tz=timezone.utc) - self.customer.current_subscription.canceled_at,
                        datetime.timedelta(seconds=1))

    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_cancel_without_stripe_sub_immediately(self, StripeCustomerMock):
        StripeCustomerMock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITHOUT_SUB)
        create_subscription(self.customer)
        self.customer.cancel_subscription(at_period_end=False)
        self.assertEqual(self.customer.current_subscription.ended_at, self.customer.current_subscription.canceled_at)

    @patch("stripe.resource.Subscription.delete")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_cancel_with_stripe_sub(self, StripeCustomerMock, SubscriptionDeleteMock):
        StripeCustomerMock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        SubscriptionDeleteMock.return_value = convert_to_fake_stripe_object(DUMMY_SUB_BASIC_CANCELED)
        create_subscription(self.customer)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        self.assertEqual(self.customer.current_subscription.status, "trialing")
        self.customer.cancel_subscription(at_period_end=False)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        self.assertEqual(self.customer.current_subscription.status, "canceled")
        self.assertEqual(self.customer.current_subscription.canceled_at, self.customer.current_subscription.ended_at)
        self.assertEqual(self.customer.current_subscription.canceled_at, convert_tstamp(CANCELED_TIME))

    @patch("stripe.resource.Subscription.delete")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_cancel_with_bad_stripe_sub(self, StripeCustomerMock, SubscriptionDeleteMock):
        StripeCustomerMock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        SubscriptionDeleteMock.return_value = convert_to_fake_stripe_object(DUMMY_SUB_BASIC_CANCELED)
        create_subscription(self.customer)
        self.assertEqual(self.customer.subscriptions.count(), 1)
        self.assertEqual(self.customer.current_subscription.status, "trialing")

        stripe_subscription = MagicMock()
        p = PropertyMock(return_value="not_sub_id")
        type(stripe_subscription).stripe_id = p

        self.customer.cancel_subscription(subscription=stripe_subscription)

        self.assertEqual(self.customer.subscriptions.count(), 1)
        self.assertEqual(self.customer.current_subscription.status, "trialing")
    
    @patch("stripe.resource.Subscription.delete")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_cancel_with_stripe_sub_future(self, stripe_customer_mock, subscription_delete_mock):
        stripe_customer_mock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        subscription_delete_mock.return_value = convert_to_fake_stripe_object(DUMMY_SUB_BASIC_CANCELED)
        subscription_instance = create_subscription(self.customer)
        subscription_instance.trial_end = timezone.now() + datetime.timedelta(days=5)
        subscription_instance.save()

        self.customer.cancel_subscription(at_period_end=True)
        self.assertEqual(self.customer.has_active_subscription(), False)
        self.assertEqual(self.customer.current_subscription.status, "canceled")

    @patch("stripe.resource.Subscription.save")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_update_quantity(self, StripeCustomerMock, SubscriptionSaveMock):
        dummy_customer = copy.deepcopy(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        dummy_customer["subscriptions"]["data"][0]["quantity"] = 2
        StripeCustomerMock.side_effect = [convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC),
                                          convert_to_fake_stripe_object(dummy_customer),
                                          convert_to_fake_stripe_object(dummy_customer)]
        create_subscription(self.customer)
        self.customer.update_plan_quantity(2, charge_immediately=False)
        self.assertEqual(self.customer.current_subscription.quantity, 2)

    @patch("stripe.resource.Customer.update_subscription")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_extend(self, StripeCustomerMock, UpdateSubscriptionMock):
        StripeCustomerMock.return_value = convert_to_fake_stripe_object(DUMMY_CUSTOMER_WITH_SUB_BASIC)
        subscription_instance = create_subscription(self.customer)
        subscription_instance.current_period_end = timezone.datetime.fromtimestamp(END_TIME, tz=timezone.utc)
        subscription_instance.save()
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
        subscription_instance.save()
        delta = timezone.timedelta(days=30)
        new_trial_end = subscription_instance.trial_end + delta
        self.customer.current_subscription.extend(delta)
        UpdateSubscriptionMock.assert_called_once_with(prorate=False, trial_end=new_trial_end)


class CurrentSubscriptionTest(TestCase):

    def setUp(self):
        self.plan_id = "test"
        self.current_subscription = Subscription.objects.create(stripe_id="sub_yyyyyyyyyyyyyy",
                                                                plan=self.plan_id,
                                                                quantity=1,
                                                                start=timezone.now(),
                                                                amount=decimal.Decimal(25.00),
                                                                status=Subscription.STATUS_PAST_DUE)

    def test_plan_display(self):
        self.assertEquals(PAYMENTS_PLANS[self.plan_id]["name"], self.current_subscription.plan_display())

    def test_status_display(self):
        self.assertEqual("Past Due", self.current_subscription.status_display())

    def test_is_period_current_no_current_period_end(self):
        self.assertFalse(self.current_subscription.is_period_current())

    def test_is_status_temporarily_current_true(self):
        current_subscription = Subscription.objects.create(stripe_id="sub_zzzzzzzzzzzzzz",
                                                           plan=self.plan_id,
                                                           quantity=1,
                                                           start=timezone.now(),
                                                           amount=decimal.Decimal(25.00),
                                                           status=Subscription.STATUS_PAST_DUE,
                                                           canceled_at=timezone.now() + datetime.timedelta(days=5),
                                                           cancel_at_period_end=True)

        self.assertTrue(current_subscription.is_status_temporarily_current())

    def test_is_status_temporarily_current_false(self):
        self.assertFalse(self.current_subscription.is_status_temporarily_current())
