# -*- coding: utf-8 -*-
"""
.. module:: dj-stripe.contrib.rest_framework.serializers
    :synopsis: dj-stripe Serializer for Subscription.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

"""

from __future__ import unicode_literals

from rest_framework.serializers import ModelSerializer
from djstripe.models import CurrentSubscription
from rest_framework import serializers


class SubscriptionSerializer(ModelSerializer):

    class Meta:
        model = CurrentSubscription


class CreateSubscriptionSerializer(serializers.Serializer):

    stripe_token = serializers.CharField(max_length=200)
    plan = serializers.CharField(max_length=200)
