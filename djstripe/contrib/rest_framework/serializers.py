"""
.. module:: dj-stripe.contrib.rest_framework.serializers.

    :synopsis: dj-stripe - Serializers to be used with the dj-stripe REST API.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

"""

from rest_framework import serializers
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.serializers import ModelSerializer, ValidationError

from djstripe.enums import SubscriptionStatus
from djstripe.models import Subscription, Customer, SetupIntent, Plan
from djstripe.settings import CANCELLATION_AT_PERIOD_END
from .mixins import AutoCustomerModelSerializerMixin


class SubscriptionSerializer(AutoCustomerModelSerializerMixin, ModelSerializer):
    """A base serializer used for the Subscription model."""

    class Meta:
        model = Subscription
        exclude = ["default_tax_rates"]

    plan = serializers.PrimaryKeyRelatedField(
        required=False, queryset=Plan.objects.all()
    )

    id = serializers.CharField(required=False)
    application_fee_percent = serializers.DecimalField(
        required=False, max_digits=5, decimal_places=2
    )
    billing = serializers.CharField(required=False)
    billing_cycle_anchor = serializers.DateTimeField(required=False)
    cancel_at_period_end = serializers.NullBooleanField(required=False)
    canceled_at = serializers.DateTimeField(required=False)
    current_period_end = serializers.DateTimeField(required=False)
    current_period_start = serializers.DateTimeField(required=False)
    customer = serializers.PrimaryKeyRelatedField(
        required=False, queryset=Customer.objects.all()
    )
    days_until_due = serializers.IntegerField(required=False)
    ended_at = serializers.DateTimeField(required=False)
    pending_setup_intent = serializers.PrimaryKeyRelatedField(
        required=False, queryset=SetupIntent.objects.all()
    )
    quantity = serializers.IntegerField(required=False)
    start = serializers.DateTimeField(required=False)
    status = serializers.CharField(required=False)
    tax_percent = serializers.DecimalField(
        required=False, max_digits=5, decimal_places=2
    )
    trial_end = serializers.DateTimeField(required=False)
    trial_start = serializers.DateTimeField(required=False)

    def create(self, validated_data):
        raise MethodNotAllowed('POST')

    def update(self, instance: Subscription, validated_data: dict):
        # We use UPDATE instead of DELETE to cancel a subscription, since
        # cancelling means change the internal state, but not remove it from the DB.

        status = validated_data.get('status')

        # It is a usual ambiguity of expressing an ACTION through REST APIs which
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


class CreateSubscriptionSerializer(SubscriptionSerializer):
    """Extend the standard SubscriptionSerializer for the case of creation,
    which must include a stripe_token field, although it doesn't belong
    to the model itself."""

    # Required on creation
    plan = serializers.PrimaryKeyRelatedField(
        required=True, queryset=Plan.objects.all()
    )

    stripe_token = serializers.CharField(max_length=200, required=True)
    charge_immediately = serializers.NullBooleanField(required=False, default=True)

    def create(self, validated_data: dict):
        stripe_token = validated_data.pop("stripe_token")
        self.customer.add_card(stripe_token)
        try:
            subscription = self.customer.subscribe(**validated_data)
            # It is key to attach a 'stripe_token' attribute to the instance to fake
            # a model property, and let the subsequent representation of the new instance
            # (recursive call to .to_representation() method) succeeds.
            subscription.stripe_token = stripe_token
        except Exception as e:
            msg = 'Something went wrong processing the payment: ' + str(e)
            raise ValidationError(detail=msg)
        else:
            return subscription


class PlanSerializer(ModelSerializer):
    class Meta:
        model = Plan
        fields = '__all__'
