"""
.. module:: dj-stripe.tests.test_contrib.test_mixins
    :synopsis: dj-stripe REST APIs Mixins Tests.

.. moduleauthor:: Cedric Foellmi (@onekiloparsec)
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.request import Request
from rest_framework.reverse import reverse
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from djstripe.contrib.rest_framework.serializers import SubscriptionSerializer

from .. import FAKE_CUSTOMER


class AutoCreateCustomerMixinTest(APITestCase):
    @patch("djstripe.models.Customer.objects.get_or_create", autospec=True)
    def test_customer_create_when_authenticated(self, mock_get_or_create):
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com", password="password"
        )
        self.assertTrue(self.client.login(username="pydanny", password="password"))
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)
        url = reverse("rest_djstripe:subscription-list")
        response = self.client.get(url)
        mock_get_or_create.assert_called_once()

    @patch("djstripe.models.Customer.objects.get_or_create", autospec=True)
    def test_customer_create_when_anonymous(self, mock_get_or_create):
        url = reverse("rest_djstripe:subscription-list")
        response = self.client.get(url)
        mock_get_or_create.assert_not_called()


class AutoCustomerModelSerializerMixinTest(APITestCase):
    def test_customer_accessor_when_authenticated(self):
        # Preparing user and customer
        user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com", password="password"
        )
        self.assertTrue(self.client.login(username="pydanny", password="password"))
        customer = FAKE_CUSTOMER.create_for_user(user)

        # Preparing request context
        factory = APIRequestFactory()
        wsgi_request = factory.get("/")
        force_authenticate(wsgi_request, user=user)

        # Performing test
        serializer = SubscriptionSerializer(context={"request": Request(wsgi_request)})
        self.assertEqual(serializer.customer, customer)

    def test_customer_accessor_when_authenticated_but_no_customer(self):
        # Preparing user and customer
        user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com", password="password"
        )
        self.assertTrue(self.client.login(username="pydanny", password="password"))

        # Preparing request context
        factory = APIRequestFactory()
        wsgi_request = factory.get("/")
        force_authenticate(wsgi_request, user=user)

        # Performing test
        serializer = SubscriptionSerializer(context={"request": Request(wsgi_request)})
        self.assertIsNone(serializer.customer)

    def test_customer_accessor_when_anonymous(self):
        # Preparing request context
        factory = APIRequestFactory()
        wsgi_request = factory.get("/")

        # Performing test
        serializer = SubscriptionSerializer(context={"request": Request(wsgi_request)})
        self.assertIsNone(serializer.customer)
