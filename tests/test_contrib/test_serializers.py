"""
.. module:: dj-stripe.tests.test_contrib.test_serializers
    :synopsis: dj-stripe Serializer Tests.

.. moduleauthor:: Philippe Luickx (@philippeluickx)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from __future__ import absolute_import, division, print_function, unicode_literals

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from mock import PropertyMock, patch

from djstripe.contrib.rest_framework.serializers import CreateSubscriptionSerializer, SubscriptionSerializer
from djstripe.enums import SubscriptionStatus
from djstripe.models import Plan

from .. import FAKE_CUSTOMER, FAKE_PLAN


class SubscriptionSerializerTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)
        self.plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

    def test_valid_serializer(self):
        now = timezone.now()
        serializer = SubscriptionSerializer(
            data={
                'stripe_id': "sub_6lsC8pt7IcFpjA",
                'customer': self.customer.id,
                'plan': self.plan.id,
                'quantity': 2,
                'start': now,
                'status': SubscriptionStatus.active,
                'current_period_end': now + timezone.timedelta(days=5),
                'current_period_start': now,
            }
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {
            'stripe_id': "sub_6lsC8pt7IcFpjA",
            'customer': self.customer,
            'plan': self.plan,
            'quantity': 2,
            'start': now,
            'status': SubscriptionStatus.active,
            'current_period_end': now + timezone.timedelta(days=5),
            'current_period_start': now,
        })
        self.assertEqual(serializer.errors, {})

    def test_invalid_serializer(self):
        now = timezone.now()
        serializer = SubscriptionSerializer(
            data={
                'stripe_id': "sub_6lsC8pt7IcFpjA",
                'customer': self.customer.id,
                'plan': self.plan.id,
                'start': now,
                'status': SubscriptionStatus.active,
                'current_period_end': now + timezone.timedelta(days=5),
                'current_period_start': now,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {})
        self.assertEqual(serializer.errors, {'quantity': ['This field is required.']})


class CreateSubscriptionSerializerTest(TestCase):

    def setUp(self):
        self.plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

    @patch("stripe.Token.create", return_value=PropertyMock(id="token_test"))
    def test_valid_serializer(self, stripe_token_mock):
        token = stripe_token_mock(card={})
        serializer = CreateSubscriptionSerializer(
            data={
                'plan': self.plan.stripe_id,
                'stripe_token': token.id,
            }
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['plan'], str(self.plan.stripe_id))
        self.assertIn('stripe_token', serializer.validated_data)
        self.assertEqual(serializer.errors, {})

    @patch("stripe.Token.create", return_value=PropertyMock(id="token_test"))
    def test_valid_serializer_non_required_fields(self, stripe_token_mock):
        """Test the CreateSubscriptionSerializer is_valid method."""
        token = stripe_token_mock(card={})
        serializer = CreateSubscriptionSerializer(
            data={
                'plan': self.plan.stripe_id,
                'stripe_token': token.id,
                'charge_immediately': True,
                'tax_percent': 13.00,
            }
        )
        self.assertTrue(serializer.is_valid())

    def test_invalid_serializer(self):
        serializer = CreateSubscriptionSerializer(
            data={
                'plan': self.plan.id,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {})
        self.assertEqual(serializer.errors, {
            'stripe_token': ['This field is required.'],
        })
