# -*- coding: utf-8 -*-
from rest_framework.permissions import BasePermission

from ...utils import subscriber_has_active_subscription
from ...settings import SUBSCRIBER_REQUEST_CALLBACK


class DJStripeSubscriptionPermission(BasePermission):

    def has_permission(self, request, view):
        """
        Check if the subscriber has an active subscription.

        Returns false if:
            * a subscriber isn't passed through the request

        See ``utils.subscriber_has_active_subscription`` for more rules.

        """

        try:
            subscriber_has_active_subscription(SUBSCRIBER_REQUEST_CALLBACK(request))
        except AttributeError:
            return False
