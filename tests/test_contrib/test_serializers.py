"""
.. module:: dj-stripe.tests.test_contrib.test_serializers
    :synopsis: dj-stripe Serializer Tests.

.. moduleauthor:: Philippe Luickx (@philippeluickx)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
from unittest.mock import PropertyMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ErrorDetail

from djstripe.contrib.rest_framework.serializers import (
    SubscriptionSerializer, CreateSubscriptionSerializer
)

from djstripe.enums import SubscriptionStatus
from djstripe.models import Plan, Subscription

from .. import FAKE_CUSTOMER, FAKE_PLAN, FAKE_PRODUCT


class SubscriptionSerializerTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

        with patch(
                "stripe.Product.retrieve",
                return_value=deepcopy(FAKE_PRODUCT),
                autospec=True,
        ):
            self.plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        now = timezone.now()
        self.subcription_data = {
            "id": "sub_6lsC8pt7IcFpjA",
            "customer": self.customer,
            "billing": "charge_automatically",
            "plan": self.plan,
            "quantity": 2,
            "start": now,
            "status": SubscriptionStatus.active,
            "current_period_end": now + timezone.timedelta(days=5),
            "current_period_start": now,
        }
        self.subscription = Subscription.objects.create(**self.subcription_data)

    @patch(
        "stripe.Token.create", return_value=PropertyMock(id="token_test"), autospec=True
    )
    def test_valid_serializer_existing_instance(self, stripe_token_mock):
        """Testing validation of serialization of an existing instance."""
        serializer = SubscriptionSerializer(self.subscription)
        self.assertIsNotNone(serializer.data)

    # This test is ambiguous as it is originally used for PUT/update methods. However,
    # creating a serializer only with data={} parameter is for creating instances,
    # hence checking the billing fields contradicts the other test below which uses the
    # dedicated CreateSubscriptionSerializer class.
    # @patch(
    #     "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    # )
    # def test_invalid_serializer_existing_instance(self, product_retrieve_mock):
    #     now = timezone.now()
    #     serializer = SubscriptionSerializer(
    #         data={
    #             "id": "sub_6lsC8pt7IcFpjA",
    #             "customer": self.customer.djstripe_id,
    #             "plan": self.plan.djstripe_id,
    #             "start": now,
    #             "status": SubscriptionStatus.active,
    #             "current_period_end": now + timezone.timedelta(days=5),
    #             "current_period_start": now,
    #         }
    #     )
    #     self.assertFalse(serializer.is_valid())
    #     self.assertEqual(serializer.validated_data, {})
    #     self.assertEqual(serializer.errors, {"billing": ["This field is required."]})


class CreateSubscriptionSerializerTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

        with patch(
                "stripe.Product.retrieve",
                return_value=deepcopy(FAKE_PRODUCT),
                autospec=True,
        ):
            self.plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

    @patch(
        "stripe.Token.create", return_value=PropertyMock(id="token_test"), autospec=True
    )
    def test_valid_serializer_wth_minimal_data(self, stripe_token_mock):
        """The serializer must be valid when provided with minimal data for instance
        creation"""
        token = stripe_token_mock(card={})
        serializer = CreateSubscriptionSerializer(
            data={"plan": self.plan.id, "stripe_token": token.id}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["plan"], str(self.plan.id))
        self.assertIn("stripe_token", serializer.validated_data)
        self.assertEqual(serializer.errors, {})

    @patch(
        "stripe.Token.create", return_value=PropertyMock(id="token_test"), autospec=True
    )
    def test_valid_serializer_with_non_required_fields(self, stripe_token_mock):
        """The serializer must be valid when provided with data including non
         reuired field for instance creation"""
        token = stripe_token_mock(card={})
        serializer = CreateSubscriptionSerializer(
            data={
                "plan": self.plan.id,
                "stripe_token": token.id,
                "charge_immediately": True,
                "tax_percent": 13.00,
            }
        )
        self.assertTrue(serializer.is_valid())

    def test_invalid_serializer_missing_stripe_token(self):
        """The serializer must be invalid when there is no stripe_token provided"""
        serializer = CreateSubscriptionSerializer(data={"plan": self.plan.id})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {})
        self.assertEqual(
            serializer.errors.get('stripe_token'),
            [ErrorDetail(string='This field is required.', code='required')]
        )

    @patch(
        "stripe.Token.create", return_value=PropertyMock(id="token_test"), autospec=True
    )
    def test_invalid_serializer_missing_plan_id(self, stripe_token_mock):
        """The serializer must be invalid when there is no stripe_token provided"""
        token = stripe_token_mock(card={})
        serializer = CreateSubscriptionSerializer(data={"stripe_token": token})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {})
        self.assertEqual(
            serializer.errors.get('plan'),
            [ErrorDetail(string='This field is required.', code='required')]
        )
