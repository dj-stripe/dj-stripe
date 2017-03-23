"""
.. module:: dj-stripe.tests.test_views
   :synopsis: dj-stripe View Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy

from django.conf import settings
from django.contrib.auth import get_user, get_user_model
from django.core.urlresolvers import reverse
from django.test.testcases import TestCase
from mock import patch

from djstripe.models import Customer, Subscription, Plan
from tests import (
    FAKE_CUSTOMER, FAKE_PLAN, FAKE_PLAN_II, FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_CANCELED, FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END
)


class AccountViewTest(TestCase):

    def setUp(self):
        self.url = reverse("djstripe:account")
        self.user = get_user_model().objects.create_user(
            username="pydanny",
            email="pydanny@gmail.com",
            password="password"
        )
        self.assertTrue(self.client.login(username="pydanny", password="password"))

        Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN_II))

    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("djstripe.models.djstripe_settings.get_idempotency_key", return_value="foo")
    def test_autocreate_customer(self, idempotency_key_mock, stripe_create_customer_mock):
        self.assertEqual(Customer.objects.count(), 0)

        response = self.client.get(self.url)

        # simply visiting the page should generate a new customer record.
        stripe_create_customer_mock.assert_called_once_with(
            api_key=settings.STRIPE_SECRET_KEY, email=self.user.email, idempotency_key="foo",
            metadata={"djstripe_subscriber": self.user.id}
        )

        self.assertEqual(FAKE_CUSTOMER["id"], response.context["customer"].stripe_id)
        self.assertEqual(self.user, response.context["customer"].subscriber)
        self.assertEqual(Customer.objects.count(), 1)

    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_plans_context(self, stripe_create_customer_mock):
        response = self.client.get(self.url)
        self.assertEqual(list(Plan.objects.all()), list(response.context["plans"]))

    def test_subscription_context_with_plan(self):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))

        response = self.client.get(self.url)
        self.assertEqual(FAKE_SUBSCRIPTION["plan"]["id"], response.context["customer"].subscription.plan.stripe_id)


class CancelSubscriptionViewTest(TestCase):
    def setUp(self):
        self.plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        self.url = reverse("djstripe:cancel_subscription")
        self.user = get_user_model().objects.create_user(
            username="pydanny",
            email="pydanny@gmail.com",
            password="password"
        )
        self.assertTrue(self.client.login(username="pydanny", password="password"))

    @patch("djstripe.stripe_objects.StripeSubscription.cancel", return_value=FAKE_SUBSCRIPTION_CANCELED)
    def test_cancel(self, cancel_subscription_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)

        response = self.client.post(self.url)

        cancel_subscription_mock.assert_called_once_with(at_period_end=True)
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(self.user.is_authenticated())

    @patch("djstripe.stripe_objects.StripeSubscription.cancel", return_value=FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END)
    def test_cancel_at_period_end(self, cancel_subscription_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)

        response = self.client.post(self.url)

        cancel_subscription_mock.assert_called_once_with(at_period_end=True)
        self.assertRedirects(response, reverse("djstripe:account"))
        self.assertTrue(self.user.is_authenticated())

    @patch("djstripe.stripe_objects.StripeSubscription.cancel", return_value=FAKE_SUBSCRIPTION_CANCELED)
    def test_cancel_next_url(self, cancel_subscription_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)

        response = self.client.post(self.url + "?next=/test")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/test")

        self.assertTrue(get_user(self.client).is_anonymous)

    @patch("djstripe.stripe_objects.StripeSubscription.cancel")
    def test_cancel_no_subscription(self, cancel_subscription_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)

        response = self.client.post(self.url)

        cancel_subscription_mock.assert_not_called()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user(self.client).is_anonymous)
