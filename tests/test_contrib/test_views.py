"""
.. module:: dj-stripe.tests.test_contrib.test_views
    :synopsis: dj-stripe Rest views for Subscription Tests.

.. moduleauthor:: Philippe Luickx (@philippeluickx)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from djstripe import settings as djstripe_settings
from djstripe.enums import SubscriptionStatus
from djstripe.models import Customer, Plan, Subscription

from .. import FAKE_CUSTOMER, FAKE_PLAN, FAKE_PRODUCT, FAKE_SUBSCRIPTION


class SubscriptionListCreateAPIViewAuthenticatedTestCase(APITestCase):
    def setUp(self):
        self.url_list = reverse("rest_djstripe:subscription-list")
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com", password="password"
        )
        self.assertTrue(self.client.login(username="pydanny", password="password"))
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

    # The return_value of .subscribe is mandatory because normal serialization fails
    # on Decimal and DateTime fields: a Mock instance is provided in place
    # because @patch and make the conversion from string impossible.
    @patch(
        "stripe.Product.retrieve", autospec=True, return_value=deepcopy(FAKE_PRODUCT)
    )
    @patch(
        "djstripe.models.Customer.subscribe", autospec=True, return_value=Subscription()
    )
    @patch("djstripe.models.Customer.add_card", autospec=True)
    def test_create_subscription(self, add_card_mock, subscribe_mock, retrieve_mock):
        """Test a POST to the Subscription List endpoint.

        Should:
            - Create a Customer object
            - Add a card to the Customer object
            - Subcribe the Customer to a plan
        """
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        data = {"plan": plan.id, "stripe_token": "cake"}
        response = self.client.post(self.url_list, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(1, Customer.objects.count())
        customer = Customer.objects.get()
        add_card_mock.assert_called_once_with(customer, "cake")
        subscribe_mock.assert_called_once_with(customer, plan, True)
        # Do not test data content in views. Values will be string representation
        # of MagicMock of the values.

    @patch(
        "stripe.Product.retrieve", autospec=True, return_value=deepcopy(FAKE_PRODUCT)
    )
    @patch(
        "djstripe.models.Customer.subscribe", autospec=True, return_value=Subscription()
    )
    @patch("djstripe.models.Customer.add_card", autospec=True)
    def test_create_subscription_charge_immediately(
        self, add_card_mock, subscribe_mock, retrieve_mock
    ):
        """Test a POST to the Subscription List endpoint.

        Should be able to accept a charge_immediately.
        This will not send an invoice to the customer on subscribe.
        """
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        data = {
            "plan": plan.id,
            "stripe_token": "cake",
            "charge_immediately": False,
        }
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(1, Customer.objects.count())
        customer = Customer.objects.get()
        subscribe_mock.assert_called_once_with(customer, plan, False)
        # Do not test data content in views. Values will be string representation
        # of MagicMock of the values.

    @patch(
        "djstripe.models.Customer.subscribe", autospec=True, return_value=Subscription()
    )
    @patch("djstripe.models.Customer.add_card", autospec=True)
    def test_create_subscription_exception(self, add_card_mock, subscribe_mock):
        """Test a POST to the SubscriptionRestView.

        Should return a 400 when an Exception is raised.
        """
        subscribe_mock.side_effect = Exception
        data = {"plan": "test0", "stripe_token": "cake"}
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_subscription_incorrect_data(self):
        """Test a POST to the SubscriptionRestView.

        Should return a 400 when a the serializer is invalid.
        """
        data = {"foo": "bar"}
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(
        "stripe.Product.retrieve", autospec=True, return_value=deepcopy(FAKE_PRODUCT)
    )
    def test_get_subscription(self, retrieve_mock):
        """Test a GET to the SubscriptionRestView.

        Should return the correct data.
        """
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        subscription = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))

        url = reverse(
            "rest_djstripe:subscription-detail", kwargs={"id": subscription.id}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["plan"], plan.id)
        self.assertEqual(response.data["status"], subscription.status)
        self.assertEqual(
            response.data["cancel_at_period_end"], subscription.cancel_at_period_end
        )

    @patch(
        "stripe.Product.retrieve", autospec=True, return_value=deepcopy(FAKE_PRODUCT)
    )
    @patch("djstripe.models.Subscription.cancel", autospec=True)
    def test_cancel_subscription(self, cancel_subscription_mock, retrieve_mock):
        """Test a cancel through a PUT method.

        Should cancel a Customer objects subscription.
        """

        def _cancel_sub(*args, **kwargs):
            subscription = Subscription.objects.first()
            subscription.status = SubscriptionStatus.canceled
            subscription.canceled_at = timezone.now()
            subscription.ended_at = timezone.now()
            subscription.save()
            return subscription

        fake_canceled_subscription = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(fake_canceled_subscription)

        cancel_subscription_mock.side_effect = _cancel_sub

        self.assertEqual(1, Subscription.objects.count())
        self.assertEqual(Subscription.objects.first().status, SubscriptionStatus.active)

        url = reverse(
            "rest_djstripe:subscription-detail", kwargs={"id": subscription.id}
        )
        response = self.client.put(url, data={"status": SubscriptionStatus.canceled})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Cancelled means flagged as canceled, so it should still be there
        self.assertEqual(1, Subscription.objects.count())
        self.assertEqual(
            Subscription.objects.first().status, SubscriptionStatus.canceled
        )

        cancel_subscription_mock.assert_called_once_with(
            Subscription.objects.first(),
            at_period_end=djstripe_settings.CANCELLATION_AT_PERIOD_END,
        )
        self.assertTrue(self.user.is_authenticated)

    @patch(
        "stripe.Product.retrieve", autospec=True, return_value=deepcopy(FAKE_PRODUCT)
    )
    @patch("djstripe.models.Subscription.cancel", autospec=True)
    def test_cancel_subscription_with_delete(self, cancel_subscription_mock, retrieve_mock):
        """Test a cancel through a DELETE method.

        Should cancel a Customer objects subscription.
        """

        def _cancel_sub(*args, **kwargs):
            subscription = Subscription.objects.first()
            subscription.status = SubscriptionStatus.canceled
            subscription.canceled_at = timezone.now()
            subscription.ended_at = timezone.now()
            subscription.save()
            return subscription

        fake_canceled_subscription = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(fake_canceled_subscription)

        cancel_subscription_mock.side_effect = _cancel_sub

        self.assertEqual(1, Subscription.objects.count())
        self.assertEqual(Subscription.objects.first().status, SubscriptionStatus.active)

        url = reverse(
            "rest_djstripe:subscription-detail", kwargs={"id": subscription.id}
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Cancelled means flagged as canceled, so it should still be there
        self.assertEqual(1, Subscription.objects.count())
        self.assertEqual(
            Subscription.objects.first().status, SubscriptionStatus.canceled
        )

        cancel_subscription_mock.assert_called_once_with(
            Subscription.objects.first(),
            at_period_end=djstripe_settings.CANCELLATION_AT_PERIOD_END,
        )
        self.assertTrue(self.user.is_authenticated)

    def test_cancel_subscription_exception(self):
        """Test a DELETE call to the Subscriptions List endpoint.

        Should return a 405, that is method is not allowed on LIST endpoint.
        """
        response = self.client.delete(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class SubscriptionListCreateAPIViewAnonymousTestCase(APITestCase):
    """
    Test the exceptions thrown by the subscription rest views.
    """

    def setUp(self):
        self.url_list = reverse("rest_djstripe:subscription-list")

    def test_create_subscription_not_logged_in(self):
        data = {"plan": "test0", "stripe_token": "cake"}
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PlanListAPIViewAnonymousTestCase(APITestCase):
    """
    Test the anonymous access to the LIST endpoint for Plans.
    """

    def setUp(self):
        self.url_list = reverse("rest_djstripe:plan-list")

    def test_get_list_of_plans(self):
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_new_plans(self):
        response = self.client.post(self.url_list, data={"nickname": "John Doe"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PlanDetailAPIViewAnonymousTestCase(APITestCase):
    """
    Test the anonymous access to the LIST endpoint for Plans.
    """

    @patch(
        "stripe.Product.retrieve", autospec=True, return_value=deepcopy(FAKE_PRODUCT)
    )
    def test_get_detail_of_plan(self, retrieve_mock):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        url = reverse("rest_djstripe:plan-detail", kwargs={"id": plan.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(
        "stripe.Product.retrieve", autospec=True, return_value=deepcopy(FAKE_PRODUCT)
    )
    def test_update_new_plans(self, retrieve_mock):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        url = reverse("rest_djstripe:plan-detail", kwargs={"id": plan.id})
        response = self.client.put(url, data={"nickname": "John Doe"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(
        "stripe.Product.retrieve", autospec=True, return_value=deepcopy(FAKE_PRODUCT)
    )
    def test_delete_new_plans(self, retrieve_mock):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        url = reverse("rest_djstripe:plan-detail", kwargs={"id": plan.id})
        response = self.client.delete(url, data={"nickname": "John Doe"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


########################################################################################
# Tests of deprecated endpoint (see urls.py)
########################################################################################
class RestSubscriptionTest(APITestCase):
    """
    Test the REST api for subscriptions.
    """

    def setUp(self):
        self.url = reverse("rest_djstripe:subscription")
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com", password="password"
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
        data = {"plan": "test0", "stripe_token": "cake"}
        response = self.client.post(self.url, data)
        self.assertEqual(1, Customer.objects.count())
        customer = Customer.objects.get()
        add_card_mock.assert_called_once_with(customer, "cake")
        subscribe_mock.assert_called_once_with(customer, "test0", True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data["charge_immediately"] = None
        self.assertEqual(response.data, data)

    @patch("djstripe.models.Customer.subscribe", autospec=True)
    @patch("djstripe.models.Customer.add_card", autospec=True)
    def test_create_subscription_charge_immediately(
            self, add_card_mock, subscribe_mock
    ):
        """Test a POST to the SubscriptionRestView.

        Should be able to accept an charge_immediately.
        This will not send an invoice to the customer on subscribe.
        """
        data = {"plan": "test0", "stripe_token": "cake", "charge_immediately": False}
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
        data = {"plan": "test0", "stripe_token": "cake"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_subscription_incorrect_data(self):
        """Test a POST to the SubscriptionRestView.

        Should return a 400 when a the serializer is invalid.
        """
        data = {"foo": "bar"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_subscription(self):
        """Test a GET to the SubscriptionRestView.

        Should return the correct data.
        """
        with patch(
                "stripe.Product.retrieve",
                return_value=deepcopy(FAKE_PRODUCT),
                autospec=True,
        ):
            plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        subscription = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["plan"], plan.djstripe_id)
        self.assertEqual(response.data["status"], subscription.status)
        self.assertEqual(
            response.data["cancel_at_period_end"], subscription.cancel_at_period_end
        )

    @patch("djstripe.models.Subscription.cancel", autospec=True)
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

        fake_canceled_subscription = deepcopy(FAKE_SUBSCRIPTION)

        with patch(
                "stripe.Product.retrieve",
                return_value=deepcopy(FAKE_PRODUCT),
                autospec=True,
        ):
            Subscription.sync_from_stripe_data(fake_canceled_subscription)

        cancel_subscription_mock.side_effect = _cancel_sub

        self.assertEqual(1, Subscription.objects.count())
        self.assertEqual(Subscription.objects.first().status, SubscriptionStatus.active)

        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Cancelled means flagged as canceled, so it should still be there
        self.assertEqual(1, Subscription.objects.count())
        self.assertEqual(
            Subscription.objects.first().status, SubscriptionStatus.canceled
        )

        cancel_subscription_mock.assert_called_once_with(
            Subscription.objects.first(),
            at_period_end=djstripe_settings.CANCELLATION_AT_PERIOD_END,
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
        data = {"plan": "test0", "stripe_token": "cake"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
