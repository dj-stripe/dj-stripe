"""
.. module:: dj-stripe.tests.test_contrib.test_views
    :synopsis: dj-stripe Rest views for Subscription Tests.

.. moduleauthor:: Philippe Luickx (@philippeluickx)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from __future__ import absolute_import, division, print_function, unicode_literals

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from djstripe import settings as djstripe_settings
from djstripe.enums import SubscriptionStatus
from djstripe.models import Customer, Plan, Subscription

from .. import FAKE_CUSTOMER, FAKE_PLAN, FAKE_SUBSCRIPTION


class RestSubscriptionTest(APITestCase):
    """
    Test the REST api for subscriptions.
    """

    def setUp(self):
        self.url = reverse("rest_djstripe:subscription")
        self.user = get_user_model().objects.create_user(
            username="pydanny",
            email="pydanny@gmail.com",
            password="password"
        )
        self.assertTrue(self.client.login(username="pydanny", password="password"))
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

    @patch("djstripe.models.Customer.subscribe", autospec=True)
    @patch("djstripe.models.Customer.add_card", autospec=True)
    def test_create_subscription(self, add_card_mock, subscribe_mock):
        """Test a POST to the SubscriptionRestView.

        Should:
            - Create a Customer object
            - Add a card to the Customer object
            - Subcribe the Customer to a plan
        """
        data = {
            "plan": "test0",
            "stripe_token": "cake",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(1, Customer.objects.count())
        customer = Customer.objects.get()
        add_card_mock.assert_called_once_with(customer, "cake")
        subscribe_mock.assert_called_once_with(customer, "test0", True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, data)

    @patch("djstripe.models.Customer.subscribe", autospec=True)
    @patch("djstripe.models.Customer.add_card", autospec=True)
    def test_create_subscription_charge_immediately(self, add_card_mock, subscribe_mock):
        """Test a POST to the SubscriptionRestView.

        Should be able to accept an charge_immediately.
        This will not send an invoice to the customer on subscribe.
        """
        data = {
            "plan": "test0",
            "stripe_token": "cake",
            "charge_immediately": False,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(1, Customer.objects.count())
        customer = Customer.objects.get()
        subscribe_mock.assert_called_once_with(customer, "test0", False)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, data)

    @patch("djstripe.models.Customer.subscribe", autospec=True)
    @patch("djstripe.models.Customer.add_card", autospec=True)
    def test_create_subscription_exception(self, add_card_mock, subscribe_mock):
        """Test a POST to the SubscriptionRestView.

        Should return a 400 when an Exception is raised.
        """
        subscribe_mock.side_effect = Exception
        data = {
            "plan": "test0",
            "stripe_token": "cake",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_subscription_incorrect_data(self):
        """Test a POST to the SubscriptionRestView.

        Should return a 400 when a the serializer is invalid.
        """
        data = {
            "foo": "bar",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_subscription(self):
        """Test a GET to the SubscriptionRestView.

        Should return the correct data.
        """
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        subscription = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["plan"], plan.id)
        self.assertEqual(response.data['status'], subscription.status)
        self.assertEqual(response.data['cancel_at_period_end'], subscription.cancel_at_period_end)

    @patch("djstripe.models.Subscription.cancel")
    def test_cancel_subscription(self, cancel_subscription_mock):
        """Test a DELETE to the SubscriptionRestView.

        Should cancel a Customer objects subscription.
        """
        def _cancel_sub(*args, **kwargs):
            subscription = Subscription.objects.first()
            subscription.status = SubscriptionStatus.canceled
            subscription.canceled_at = timezone.now()
            subscription.ended_at = timezone.now()
            subscription.save()
            return subscription

        fake_cancelled_subscription = deepcopy(FAKE_SUBSCRIPTION)
        Subscription.sync_from_stripe_data(fake_cancelled_subscription)

        cancel_subscription_mock.side_effect = _cancel_sub

        self.assertEqual(1, Subscription.objects.count())
        self.assertEqual(Subscription.objects.first().status, SubscriptionStatus.active)

        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Cancelled means flagged as cancelled, so it should still be there
        self.assertEqual(1, Subscription.objects.count())
        self.assertEqual(Subscription.objects.first().status, SubscriptionStatus.canceled)

        cancel_subscription_mock.assert_called_once_with(
            at_period_end=djstripe_settings.CANCELLATION_AT_PERIOD_END
        )
        self.assertTrue(self.user.is_authenticated)

    def test_cancel_subscription_exception(self):
        """Test a DELETE to the SubscriptionRestView.

        Should return a 400 when an exception is raised.
        """
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RestSubscriptionNotLoggedInTest(APITestCase):
    """
    Test the exceptions thrown by the subscription rest views.
    """
    def setUp(self):
        self.url = reverse("rest_djstripe:subscription")

    def test_create_subscription_not_logged_in(self):
        data = {
            "plan": "test0",
            "stripe_token": "cake",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
