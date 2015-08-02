"""
.. module:: dj-stripe.tests.test_contrib.test_serializers
    :synopsis: dj-stripe Serializer Tests.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

"""

from __future__ import unicode_literals

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from django.conf import settings

from mock import patch, PropertyMock
from djstripe.contrib.rest_framework.serializers import SubscriptionSerializer, CreateSubscriptionSerializer
from djstripe.models import Subscription


class SubscriptionSerializerTest(TestCase):

    def test_valid_serializer(self):
        now = timezone.now()
        serializer = SubscriptionSerializer(
            data={
                'stripe_id': 'sub_yyyyyyyyyyyyyy',
                'plan': settings.DJSTRIPE_PLANS['test0']['plan'],
                'quantity': 2,
                'start': now,
                'status': Subscription.STATUS_ACTIVE,
                'amount': settings.DJSTRIPE_PLANS['test0']['price'],
            }
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {
            'stripe_id': 'sub_yyyyyyyyyyyyyy',
            'plan': 'test0',
            'quantity': 2,
            'start': now,
            'status': 'active',
            'amount': Decimal('1000'),
        })
        self.assertEqual(serializer.errors, {})

    def test_invalid_serializer(self):
        now = timezone.now()
        serializer = SubscriptionSerializer(
            data={
                'stripe_id': 'sub_yyyyyyyyyyyyyy',
                'plan': settings.DJSTRIPE_PLANS['test0']['plan'],
                'start': now,
                'status': Subscription.STATUS_ACTIVE,
                'amount': settings.DJSTRIPE_PLANS['test0']['price'],
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {})
        self.assertEqual(serializer.errors, {'quantity': ['This field is required.']})


class CreateSubscriptionSerializerTest(TestCase):

    @patch("stripe.Token.create", return_value=PropertyMock(id="token_test"))
    def test_valid_serializer(self, stripe_token_mock):
        token = stripe_token_mock(card={})
        serializer = CreateSubscriptionSerializer(
            data={
                'plan': settings.DJSTRIPE_PLANS['test0']['plan'],
                'stripe_token': token.id,
            }
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['plan'], 'test0')
        self.assertIn('stripe_token', serializer.validated_data)
        self.assertEqual(serializer.errors, {})

    def test_invalid_serializer(self):
        serializer = CreateSubscriptionSerializer(
            data={
                'plan': settings.DJSTRIPE_PLANS['test0']['plan'],
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {})
        self.assertEqual(serializer.errors, {
            'stripe_token': ['This field is required.'],
        })
