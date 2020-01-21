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

from djstripe.contrib.rest_framework.serializers import (
    CreateSubscriptionSerializer,
    SubscriptionSerializer,
)
from djstripe.enums import SubscriptionStatus
from djstripe.models import Plan

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

    def test_valid_serializer(self):
        now = timezone.now()
        serializer = SubscriptionSerializer(
            data={
                "id": "sub_6lsC8pt7IcFpjA",
                "collection_method": "charge_automatically",
                "customer": self.customer.djstripe_id,
                "plan": self.plan.djstripe_id,
                "quantity": 2,
                "start": now,
                "status": SubscriptionStatus.active,
                "current_period_end": now + timezone.timedelta(days=5),
                "current_period_start": now,
            }
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            serializer.validated_data,
            {
                "id": "sub_6lsC8pt7IcFpjA",
                "collection_method": "charge_automatically",
                "customer": self.customer,
                "plan": self.plan,
                "quantity": 2,
                "start": now,
                "status": SubscriptionStatus.active,
                "current_period_end": now + timezone.timedelta(days=5),
                "current_period_start": now,
            },
        )
        self.assertEqual(serializer.errors, {})

    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_invalid_serializer(self, product_retrieve_mock):
        now = timezone.now()
        serializer = SubscriptionSerializer(
            data={
                "id": "sub_6lsC8pt7IcFpjA",
                "customer": self.customer.djstripe_id,
                "plan": self.plan.djstripe_id,
                "start": now,
                "status": SubscriptionStatus.active,
                "current_period_end": now + timezone.timedelta(days=5),
                "current_period_start": now,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {})
        self.assertEqual(
            serializer.errors, {"collection_method": ["This field is required."]}
        )


class CreateSubscriptionSerializerTest(TestCase):
    def setUp(self):
        with patch(
            "stripe.Product.retrieve",
            return_value=deepcopy(FAKE_PRODUCT),
            autospec=True,
        ):
            self.plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

    @patch(
        "stripe.Token.create", return_value=PropertyMock(id="token_test"), autospec=True
    )
    def test_valid_serializer(self, stripe_token_mock):
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
    def test_valid_serializer_non_required_fields(self, stripe_token_mock):
        """Test the CreateSubscriptionSerializer is_valid method."""
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

    def test_invalid_serializer(self):
        serializer = CreateSubscriptionSerializer(data={"plan": self.plan.id})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {})
        self.assertEqual(
            serializer.errors, {"stripe_token": ["This field is required."]}
        )
