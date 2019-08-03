"""
.. module:: dj-stripe.contrib.rest_framework.permissions.

    :synopsis: dj-stripe - Permissions to be used with the dj-stripe REST API.

.. moduleauthor:: @kavdev, @pydanny

"""
from rest_framework.permissions import BasePermission

from ...settings import subscriber_request_callback
from ...utils import subscriber_has_active_subscription


class DJStripeSubscriptionPermission(BasePermission):
    """
    A permission to be used when wanting to permit users with active subscriptions.
    """

    def has_permission(self, request, view):
        """
        Check if the subscriber has an active subscription.

        Returns false if:
            * a subscriber isn't passed through the request

        See ``utils.subscriber_has_active_subscription`` for more rules.

        """
        try:
            subscriber_has_active_subscription(subscriber_request_callback(request))
        except AttributeError:
            return False
