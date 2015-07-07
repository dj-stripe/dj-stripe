"""
.. module:: dj-stripe.tests.test_contrib.test_views
    :synopsis: dj-stripe Rest views for Subscription Tests.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

"""

from __future__ import unicode_literals

from decimal import Decimal

from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse

from mock import patch, PropertyMock
from rest_framework import status
from rest_framework.test import APITestCase

from djstripe.models import Subscription, Customer
from djstripe import settings as djstripe_settings

if settings.STRIPE_PUBLIC_KEY and settings.STRIPE_SECRET_KEY:
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY


class RestSubscriptionTest(APITestCase):
    """
    Test the REST api for subscriptions.
    """
    def setUp(self):
        self.url = reverse("rest_djstripe:subscription")
        self.user = get_user_model().objects.create_user(
            username="testuser",
            email="test@example.com",
            password="123"
        )

        self.assertTrue(self.client.login(username="testuser", password="123"))

    @patch("djstripe.models.Customer.subscribe", autospec=True)
    @patch("djstripe.models.Customer.update_card", autospec=True)
    @patch("stripe.Customer.create", return_value=PropertyMock(id="cus_xxx1234567890"))
    def test_create_subscription(self, stripe_customer_mock, update_card_mock, subscribe_mock):
        self.assertEqual(0, Customer.objects.count())
        data = {
            "plan": "test0",
            "stripe_token": "cake",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(1, Customer.objects.count())
        update_card_mock.assert_called_once_with(self.user.customer, "cake")
        subscribe_mock.assert_called_once_with(self.user.customer, "test0")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, data)

    @patch("djstripe.models.Customer.subscribe", autospec=True)
    @patch("djstripe.models.Customer.update_card", autospec=True)
    @patch("stripe.Customer.create", return_value=PropertyMock(id="cus_xxx1234567890"))
    def test_create_subscription_exception(self, stripe_customer_mock, update_card_mock, subscribe_mock):
        e = Exception
        subscribe_mock.side_effect = e
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
        fake_customer = Customer.objects.create(
            stripe_id="cus_xxx1234567890",
            subscriber=self.user
        )
        Subscription.objects.create(
            stripe_id="sub_yyyyyyyyyyyyyy",
            customer=fake_customer,
            plan="test",
            quantity=1,
            start=timezone.now(),
            amount=Decimal(25.00),
            status="active",
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["plan"], "test")
        self.assertEqual(response.data['status'], 'active')
        self.assertEqual(response.data['cancel_at_period_end'], False)

    @patch("djstripe.models.Customer.cancel_subscription", return_value=Subscription(status=Subscription.STATUS_ACTIVE))
    @patch("djstripe.models.Customer.current_subscription", new_callable=PropertyMock, return_value=Subscription(plan="test", amount=Decimal(25.00), status="active"))
    @patch("djstripe.models.Customer.subscribe", autospec=True)
    def test_cancel_subscription(self, subscribe_mock, stripe_create_customer_mock, cancel_subscription_mock):
        fake_customer = Customer.objects.create(
            stripe_id="cus_xxx1234567890",
            subscriber=self.user
        )
        Subscription.objects.create(
            stripe_id="sub_yyyyyyyyyyyyyy",
            customer=fake_customer,
            plan="test",
            quantity=1,
            start=timezone.now(),
            amount=Decimal(25.00),
            status="active",
        )
        self.assertEqual(1, Subscription.objects.count())

        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Cancelled means flagged as cancelled, so it should still be there
        self.assertEqual(1, Subscription.objects.count())

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
