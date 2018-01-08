# -*- coding: utf-8 -*-
"""
.. module:: dj-stripe.contrib.rest_framework.views.

    :synopsis: Views for the dj-stripe REST API.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

"""

from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import Customer
from ...settings import CANCELLATION_AT_PERIOD_END, subscriber_request_callback
from .serializers import CreateSubscriptionSerializer, SubscriptionSerializer


class SubscriptionRestView(APIView):
    """API Endpoints for the Subscription object."""

    permission_classes = (IsAuthenticated,)

    def get(self, request, **kwargs):
        """
        Return the customer's valid subscriptions.

        Returns with status code 200.
        """
        customer, _created = Customer.get_or_create(
            subscriber=subscriber_request_callback(self.request),
        )

        serializer = SubscriptionSerializer(customer.subscription)
        return Response(serializer.data)

    def post(self, request, **kwargs):
        """
        Create a new current subscription for the user.

        Returns with status code 201.
        """
        serializer = CreateSubscriptionSerializer(data=request.data)

        if serializer.is_valid():
            try:
                customer, _created = Customer.get_or_create(
                    subscriber=subscriber_request_callback(self.request)
                )
                customer.add_card(serializer.data["stripe_token"])
                customer.subscribe(
                    serializer.data["plan"],
                    serializer.data.get("charge_immediately", True)
                )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception:
                # TODO: Better error messages
                return Response(
                    "Something went wrong processing the payment.",
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, **kwargs):
        """
        Mark the customers current subscription as cancelled.

        Returns with status code 204.
        """
        try:
            customer, _created = Customer.get_or_create(subscriber=subscriber_request_callback(self.request))
            customer.subscription.cancel(at_period_end=CANCELLATION_AT_PERIOD_END)

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            return Response("Something went wrong cancelling the subscription.", status=status.HTTP_400_BAD_REQUEST)
