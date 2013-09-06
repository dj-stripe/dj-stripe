from rest_framework.permissions import BasePermission

from ...models import Customer


class DJStripeSubscriptionPermission(BasePermission):

    def has_permission(self, request, view):

        if request.user is None:
            # No user? Then they don't have permission!
            return False

        # get the user's customer object
        customer, created = Customer.get_or_create(user=request.user)

        if created:
            # If just created, then they can't possibly have a subscription.
            # Since customer.has_active_subscription() does at least one query,
            #   we send them on their way without permission.
            return False

        # Do formal check to see if user with permission has an active subscription.
        return customer.has_active_subscription()
