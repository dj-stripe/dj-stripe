# -*- coding: utf-8 -*-
"""
.. module:: dj-stripe.contrib.rest_framework.serializers
    :synopsis: dj-stripe Serializer for Subscription.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

"""

from __future__ import unicode_literals

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from djstripe.models import Subscription


class SubscriptionSerializer(ModelSerializer):

    class Meta(object):
        model = Subscription


class CreateSubscriptionSerializer(serializers.Serializer):
    """A serializer used to create a Subscription."""

    stripe_token = serializers.CharField(max_length=200)
    plan = serializers.CharField(max_length=50)
    charge_immediately = serializers.NullBooleanField(required=False)
    tax_percent = serializers.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
    )
