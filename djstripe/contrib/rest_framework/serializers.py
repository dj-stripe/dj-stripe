"""
.. module:: dj-stripe.contrib.rest_framework.serializers.

    :synopsis: dj-stripe - Serializers to be used with the dj-stripe REST API.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

"""

from rest_framework import serializers
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.serializers import ModelSerializer, ValidationError

from djstripe.enums import SubscriptionStatus
from djstripe.models import Plan, Subscription
from djstripe.settings import CANCELLATION_AT_PERIOD_END

from .mixins import AutoCustomerModelSerializerMixin


class SubscriptionSerializer(AutoCustomerModelSerializerMixin, ModelSerializer):
    """A base serializer used for the Subscription model."""

    class Meta:
        model = Subscription
        exclude = ["default_tax_rates"]

    # StripeModel fields
    id = serializers.CharField(required=False)
    created = serializers.DateTimeField(required=False)
    metadata = serializers.JSONField(required=False)
    description = serializers.CharField(required=False)

    # Subscription-specific fields
    application_fee_percent = serializers.DecimalField(
        required=False, max_digits=5, decimal_places=2
    )
    billing_cycle_anchor = serializers.DateTimeField(required=False)
    cancel_at_period_end = serializers.NullBooleanField(required=False)
    canceled_at = serializers.DateTimeField(required=False)
    collection_method = serializers.CharField(required=False)
    current_period_end = serializers.DateTimeField(required=False)
    current_period_start = serializers.DateTimeField(required=False)
    customer = serializers.SlugField(required=False, source="customer.id")
    days_until_due = serializers.IntegerField(required=False)
    default_payment_method = serializers.SlugField(
        required=False, source="default_payment_method.id"
    )
    default_source = serializers.SlugField(required=False, source="default_source.id")
    discount = serializers.JSONField(required=False)
    ended_at = serializers.DateTimeField(required=False)
    next_pending_invoice_item_invoice = serializers.DateTimeField(required=False)
    pending_invoice_item_interval = serializers.JSONField(required=False)
    pending_setup_intent = serializers.SlugField(
        required=False, source="pending_setup_intent.id"
    )
    pending_update = serializers.JSONField(required=False)
    plan = serializers.SlugField(required=False, source="plan.id")
    quantity = serializers.IntegerField(required=False)
    start = serializers.DateTimeField(required=False)
    start_date = serializers.DateTimeField(required=False)
    status = serializers.CharField(required=False)
    tax_percent = serializers.DecimalField(
        required=False, max_digits=5, decimal_places=2
    )
    trial_end = serializers.DateTimeField(required=False)
    trial_start = serializers.DateTimeField(required=False)

    def validate_status(self, value):
        if value not in dir(SubscriptionStatus):
            raise ValidationError(
                {"detail": "Invalid SubscriptionStatus {}".format(value)}
            )
        return value

    def create(self, validated_data):
        raise MethodNotAllowed("POST")

    def update(self, instance: Subscription, validated_data: dict):
        # We use UPDATE instead of DELETE to cancel a subscription, since
        # cancelling means change the internal state, but not remove it from the DB.

        status = validated_data.get("status")

        # It is a usual ambiguity of expressing an ACTION through REST APIs which
        # are fundamentally based on manipulating resources.
        if status == SubscriptionStatus.canceled != instance.status:
            try:
                instance.cancel(at_period_end=CANCELLATION_AT_PERIOD_END)
            except Exception as e:
                msg = "Something went wrong cancelling the subscription: " + str(e)
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
    plan = serializers.SlugField(required=True, source="plan.id")
    stripe_token = serializers.CharField(max_length=200, required=True)
    charge_immediately = serializers.NullBooleanField(required=False, default=True)

    def validate(self, attrs):
        # Since we use source=plan.id in field declaration, one must overcome its
        # nested nature when validating the final data. This can't be done in a
        # specialized validate_plan function (where the value will appear as provided
        # in POST request, that is, the correct ID slug string.)
        plan_id = attrs.pop("plan").get("id")

        if Plan.objects.filter(id=plan_id).exists():
            attrs.update(plan=Plan.objects.get(id=plan_id))
        else:
            msg = "Unknown / invalid Plan id: " + str(attrs.get("plan"))
            raise ValidationError(detail=msg)

        return attrs

    def create(self, validated_data: dict):
        stripe_token = validated_data.pop("stripe_token")
        self.customer.add_card(stripe_token)
        try:
            subscription = self.customer.subscribe(**validated_data)
        except Exception as e:
            msg = "Something went wrong processing the payment: " + str(e)
            raise ValidationError(detail=msg)
        else:
            # Plan instance is missing after subscribe. Bug in _api_create()?
            # But plan instance is nonetheless mandatory for to_representation()
            # to succeed.
            subscription.plan = validated_data.get("plan")
            # It is key to attach a 'stripe_token' attribute to the instance to fake
            # a model property, and let the subsequent representation of the new
            # instance (recursive call to .to_representation() method) succeeds.
            subscription.stripe_token = stripe_token
            return subscription


class PlanSerializer(ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "id",
            "created",
            "metadata",
            "description",
            "active",
            "aggregate_usage",
            "amount",
            "billing_scheme",
            "currency",
            "interval",
            "interval_count",
            "nickname",
            "product",
            "tiers",
            "tiers_mode",
            "transform_usage",
            "trial_period_days",
            "usage_type",
            "name",
            "statement_descriptor",
        )

    # StripeModel fields
    id = serializers.SlugField(required=False)
    created = serializers.DateTimeField(required=False)
    metadata = serializers.JSONField(required=False)
    description = serializers.CharField(required=False)

    # Plan-specific fields
    active = serializers.BooleanField()
    aggregate_usage = serializers.CharField(required=False)
    amount = serializers.DecimalField(required=False, max_digits=11, decimal_places=2)
    billing_scheme = serializers.CharField(required=False)
    currency = serializers.CharField(required=False)
    interval = serializers.CharField()
    interval_count = serializers.IntegerField(required=False)
    nickname = serializers.CharField(required=False)
    product = serializers.SlugField(required=True, source="product.id")
    tiers = serializers.JSONField(required=False)
    tiers_mode = serializers.CharField(required=False)
    transform_usage = serializers.JSONField(required=False)
    trial_period_days = serializers.IntegerField(required=False)
    usage_type = serializers.CharField()

    # Legacy fields (pre 2017-08-15)
    name = serializers.CharField(required=False)
    statement_descriptor = serializers.CharField(required=False)


########################################################################################
# Deprecated serializers (used in deprecated API view)
########################################################################################
class DeprecatedSubscriptionSerializer(ModelSerializer):
    """A serializer used for the Subscription model."""

    class Meta:
        """Model class options."""

        model = Subscription
        exclude = ["default_tax_rates"]


class DeprecatedCreateSubscriptionSerializer(serializers.Serializer):
    """A serializer used to create a Subscription."""

    stripe_token = serializers.CharField(max_length=200)
    plan = serializers.CharField(max_length=50)
    charge_immediately = serializers.NullBooleanField(required=False)
    tax_percent = serializers.DecimalField(
        required=False, max_digits=5, decimal_places=2
    )
