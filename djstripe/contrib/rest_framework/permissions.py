# -*- coding: utf-8 -*-
from rest_framework.permissions import BasePermission

from ...utils import customer_has_active_subscription
from ...settings import CUSTOMER_REQUEST_CALLBACK


class DJStripeSubscriptionPermission(BasePermission):

    def has_permission(self, request, view):
        """
        Check if the customer has an active subscription.

        Returns false if:
            * a customer isn't passed through the request

        See ``utils.customer_has_active_subscription`` for more rules.

        """

        try:
            customer_has_active_subscription(CUSTOMER_REQUEST_CALLBACK(request))
        except AttributeError:
            return False
