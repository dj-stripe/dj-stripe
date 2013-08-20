from rest_framework.permissions import BasePermission

from ..models import Customer


class DJStripePermission(BasePermission):

    def has_permission(self, request, view):
        # get the user's customer object
        customer, created = Customer.get_or_create(user=request.user)
        if created:
            return False

        return customer.has_active_subscription()
