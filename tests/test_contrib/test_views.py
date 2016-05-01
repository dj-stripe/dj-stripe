"""
.. module:: dj-stripe.tests.test_contrib.test_views
    :synopsis: dj-stripe Rest views for Subscription Tests.

.. moduleauthor:: Philippe Luickx (@philippeluickx)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from __future__ import unicode_literals

from copy import deepcopy
from decimal import Decimal
from unittest.case import skip

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.utils import timezone
from mock import patch, PropertyMock
from rest_framework import status
from rest_framework.test import APITestCase

from djstripe import settings as djstripe_settings
from djstripe.models import Subscription, Customer, Plan
from tests import FAKE_SUBSCRIPTION, FAKE_PLAN


class RestSubscriptionTest(APITestCase):
    """
    Test the REST api for subscriptions.
    """

    def setUp(self):
        self.url = reverse("rest_djstripe:subscription")
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com", password="password")

        self.assertTrue(self.client.login(username="pydanny", password="password"))

    @patch("djstripe.models.Customer.subscribe", autospec=True)
    @patch("djstripe.models.Customer.add_card", autospec=True)
    @patch("stripe.Customer.create", return_value=PropertyMock(id="cus_xxx1234567890"))
    def test_create_subscription(self, stripe_customer_create_mock, add_card_mock, subscribe_mock):
        self.assertEqual(0, Customer.objects.count())
        data = {
            "plan": "test0",
            "stripe_token": "cake",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(1, Customer.objects.count())
        add_card_mock.assert_called_once_with(self.user.customer, "cake")
        subscribe_mock.assert_called_once_with(self.user.customer, "test0")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, data)

    @patch("djstripe.models.Customer.subscribe", autospec=True)
    @patch("djstripe.models.Customer.add_card", autospec=True)
    @patch("stripe.Customer.create", return_value=PropertyMock(id="cus_xxx1234567890"))
    def test_create_subscription_exception(self, stripe_customer_create_mock, add_card_mock, subscribe_mock):
        subscribe_mock.side_effect = Exception
        data = {
            "plan": "test0",
            "stripe_token": "cake",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_no_content_for_subscription(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_get_subscription(self):
        Customer.objects.create(subscriber=self.user, stripe_id="cus_6lsBvm5rJ0zyHc", currency="usd")
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        subscription = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["plan"], plan.id)
        self.assertEqual(response.data['status'], subscription.status)
        self.assertEqual(response.data['cancel_at_period_end'], subscription.cancel_at_period_end)

    @patch("djstripe.models.Customer.cancel_subscription")
    def test_cancel_subscription(self, cancel_subscription_mock):
        def _cancel_sub(*args, **kwargs):
            subscription = Subscription.objects.first()
            subscription.status = Subscription.STATUS_CANCELLED
            subscription.canceled_at = timezone.now()
            subscription.ended_at = timezone.now()
            subscription.save()
            return subscription

        fake_cancelled_subscription = deepcopy(FAKE_SUBSCRIPTION)
        Customer.objects.create(subscriber=self.user, stripe_id="cus_6lsBvm5rJ0zyHc", currency="usd")
        subscription = Subscription.sync_from_stripe_data(fake_cancelled_subscription)

        cancel_subscription_mock.side_effect = _cancel_sub

        self.assertEqual(1, Subscription.objects.count())
        self.assertEqual(Subscription.objects.first().status, Subscription.STATUS_ACTIVE)

        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Cancelled means flagged as cancelled, so it should still be there
        self.assertEqual(1, Subscription.objects.count())
        self.assertEqual(Subscription.objects.first().status, Subscription.STATUS_CANCELLED)

        cancel_subscription_mock.assert_called_once_with(
            at_period_end=djstripe_settings.CANCELLATION_AT_PERIOD_END
        )
        self.assertTrue(self.user.is_authenticated())

    def test_cancel_subscription_exception(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_subscription_incorrect_data(self):
        self.assertEqual(0, Customer.objects.count())
        data = {
            "foo": "bar",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(0, Customer.objects.count())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RestSubscriptionNotLoggedInTest(APITestCase):
    """
    Test the exceptions thrown by the subscription rest views.
    """
    def setUp(self):
        self.url = reverse("rest_djstripe:subscription")

    def test_create_subscription_not_logged_in(self):
        self.assertEqual(0, Customer.objects.count())
        data = {
            "plan": "test0",
            "stripe_token": "cake",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(0, Customer.objects.count())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
