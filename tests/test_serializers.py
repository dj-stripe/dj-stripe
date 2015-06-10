from __future__ import unicode_literals

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

from djstripe.serializers import (
    SubscriptionSerializer,
    CreateSubscriptionSerializer,
)
from djstripe.models import (
    CurrentSubscription,
    Customer,
)
if settings.STRIPE_PUBLIC_KEY and settings.STRIPE_SECRET_KEY:
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY


class SubscriptionSerializerTest(TestCase):

    def setup(self):
        pass

    def test_valid_serializer(self):
        now = timezone.now()
        serializer = SubscriptionSerializer(
            data={
                'plan': settings.DJSTRIPE_PLANS['test0']['plan'],
                'quantity': 2,
                'start': now,
                'status': CurrentSubscription.STATUS_ACTIVE,
                'amount': settings.DJSTRIPE_PLANS['test0']['price'],
            }
        )
        assert serializer.is_valid()
        assert serializer.validated_data == {
            'plan': 'test0',
            'quantity': 2,
            'start': now,
            'status': 'active',
            'amount': Decimal('1000'),
        }
        assert serializer.errors == {}

    def test_invalid_serializer(self):
        now = timezone.now()
        serializer = SubscriptionSerializer(
            data={
                'plan': settings.DJSTRIPE_PLANS['test0']['plan'],
                'start': now,
                'status': CurrentSubscription.STATUS_ACTIVE,
                'amount': settings.DJSTRIPE_PLANS['test0']['price'],
            }
        )
        assert not serializer.is_valid()
        assert serializer.validated_data == {}
        assert serializer.errors == {'quantity': ['This field is required.']}


class CreateSubscriptionSerializerTest(TestCase):

    def setup(self):
        pass

    def test_valid_serializer(self):
        token = stripe.Token.create(
            card={
                'number': '4242424242424242',
                'exp_month': 12,
                'exp_year': 2020,
                'cvc': '123',
            }
        )
        serializer = CreateSubscriptionSerializer(
            data={
                'plan': settings.DJSTRIPE_PLANS['test0']['plan'],
                'stripe_token': token.id,
            }
        )
        print serializer.is_valid()
        print serializer.validated_data
        assert serializer.is_valid()
        assert serializer.validated_data['plan'] == 'test0'
        self.assertIn('stripe_token', serializer.validated_data)
        assert serializer.errors == {}

    def test_invalid_serializer(self):
        serializer = CreateSubscriptionSerializer(
            data={
                'plan': settings.DJSTRIPE_PLANS['test0']['plan'],
            }
        )
        assert not serializer.is_valid()
        assert serializer.validated_data == {}
        assert serializer.errors == {
            'stripe_token': ['This field is required.'],
        }
