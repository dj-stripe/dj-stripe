"""
.. module:: dj-stripe.contrib.rest_framework.serializers.

    :synopsis: dj-stripe - Serializers to be used with the dj-stripe REST API.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

"""

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from djstripe.models import Subscription


class SubscriptionSerializer(ModelSerializer):
    """A serializer used for the Subscription model."""

    class Meta:
        """Model class options."""

        model = Subscription
        exclude = ["default_tax_rates"]


class CreateSubscriptionSerializer(serializers.Serializer):
    """A serializer used to create a Subscription."""

    stripe_token = serializers.CharField(max_length=200)
    plan = serializers.CharField(max_length=50)
    charge_immediately = serializers.NullBooleanField(required=False)
    tax_percent = serializers.DecimalField(
        required=False, max_digits=5, decimal_places=2
    )
