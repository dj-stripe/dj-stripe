"""
.. module:: dj-stripe.tests.test_views
   :synopsis: dj-stripe View Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy

from django.contrib.auth import get_user, get_user_model
from django.test.testcases import TestCase
from django.urls import reverse
from mock import patch

from djstripe.models import Customer, Subscription, Plan
from tests import (
    FAKE_CUSTOMER, FAKE_PLAN, FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_CANCELED, FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END
)


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
        self.assertTrue(self.user.is_authenticated)

    @patch("djstripe.stripe_objects.StripeSubscription.cancel", return_value=FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END)
    def test_cancel_at_period_end(self, cancel_subscription_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)

        response = self.client.post(self.url)

        cancel_subscription_mock.assert_called_once_with(at_period_end=True)
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(self.user.is_authenticated)

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
