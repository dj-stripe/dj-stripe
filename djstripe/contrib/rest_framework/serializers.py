"""
.. module:: dj-stripe.contrib.rest_framework.serializers.

    :synopsis: dj-stripe - Serializers to be used with the dj-stripe REST API.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

"""

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, ValidationError

from djstripe.enums import SubscriptionStatus
from djstripe.models import Subscription
from djstripe.settings import CANCELLATION_AT_PERIOD_END
from .mixins import AutoCustomerModelSerializerMixin


class SubscriptionSerializer(AutoCustomerModelSerializerMixin, ModelSerializer):
    """A serializer used for the Subscription model."""

    class Meta:
        """Model class options."""

        model = Subscription
        exclude = ["default_tax_rates"]

    stripe_token = serializers.CharField(max_length=200, required=True)
    plan = serializers.CharField(max_length=50, required=True)

    def create(self, validated_data: dict):
        self.customer.add_card(validated_data.pop("stripe_token"))
        try:
            subscription = self.customer.subscribe(**validated_data)
        except Exception as e:
            msg = 'Something went wrong processing the payment: ' + str(e)
            raise ValidationError(detail=msg)
        else:
            return subscription

    def update(self, instance: Subscription, validated_data: dict):
        # We use UPDATE instead of DELETE to cancel a subscription, since
        # cancelling means change the internal state, but not remove it from the DB.

        status = validated_data.get('status')

        # It is usual ambiguity of expressing a ACTION through REST APIs which
        # are fundamentally based on manipulating resources.
        if status == SubscriptionStatus.canceled != instance.status:
            try:
                instance.cancel(at_period_end=CANCELLATION_AT_PERIOD_END)
            except Exception as e:
                msg = 'Something went wrong cancelling the subscription: ' + str(e)
                raise ValidationError(detail=msg)

        # Applying the update of all other fields.
        Subscription.objects.filter(pk=instance.pk).update(**validated_data)
        instance.refresh_from_db()
        return instance
