"""
.. module:: dj-stripe.tests.test_views
   :synopsis: dj-stripe View Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from copy import deepcopy

from django.contrib.auth import get_user, get_user_model
from django.test.testcases import TestCase
from django.urls import reverse
from mock import patch

from djstripe.models import Customer, Plan, Subscription

from . import (
    FAKE_CUSTOMER, FAKE_PLAN, FAKE_SUBSCRIPTION, FAKE_SUBSCRIPTION_CANCELED, FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END
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
        stripe_customer = Customer.sync_from_stripe_data(FAKE_CUSTOMER)
        stripe_customer.subscriber = self.user
        stripe_customer.save()

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("djstripe.models.Subscription._api_delete", return_value=FAKE_SUBSCRIPTION_CANCELED)
    def test_cancel(self, cancel_subscription_mock, customer_retrieve_mock):
        Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)

        response = self.client.post(self.url)

        cancel_subscription_mock.assert_called_once_with(at_period_end=True)
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(self.user.is_authenticated)

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("djstripe.models.Subscription._api_delete", return_value=FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END)
    def test_cancel_at_period_end(self, cancel_subscription_mock, customer_retrieve_mock):
        Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)

        response = self.client.post(self.url)

        cancel_subscription_mock.assert_called_once_with(at_period_end=True)
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(self.user.is_authenticated)

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("djstripe.models.Subscription._api_delete", return_value=FAKE_SUBSCRIPTION_CANCELED)
    def test_cancel_next_url(self, cancel_subscription_mock, customer_retrieve_mock):
        Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)

        response = self.client.post(self.url + "?next=/test")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/test")

        self.assertTrue(get_user(self.client).is_anonymous)

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("djstripe.models.Subscription._api_delete")
    def test_cancel_no_subscription(self, cancel_subscription_mock, customer_retrieve_mock):
        response = self.client.post(self.url)

        cancel_subscription_mock.assert_not_called()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user(self.client).is_anonymous)
