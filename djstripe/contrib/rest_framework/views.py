"""
.. module:: dj-stripe.contrib.rest_framework.views.

    :synopsis: Views for the dj-stripe REST API.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

"""

from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from ...models import Subscription, Plan
from ...settings import subscriber_request_callback
from .serializers import (
    SubscriptionSerializer, CreateSubscriptionSerializer, PlanSerializer
)
from .permissions import IsSubscriptionOwner
from .mixins import AutoCreateCustomerMixin


class SubscriptionListView(AutoCreateCustomerMixin, ListCreateAPIView):
    """API Endpoints for the Subscription object.

    See the serializer methods about how the creation of a Subscription is
    handled.
    """

    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method.upper() == 'POST':
            return CreateSubscriptionSerializer
        return SubscriptionSerializer

    def get_queryset(self):
        """Override of the class property `queryset` to ensure the Subscriptions
        returned are those of the authenticated user.
        """
        # It is neither the role of a GET method (which should have no effect on data),
        # nor that of a _Subscription_ endpoint to check for an existing customer,
        # or create one if necessary. See AutoCreateCustomerMixin.
        subscriber = subscriber_request_callback(self.request)
        return Subscription.objects.filter(customer__subscriber=subscriber)


class SubscriptionDetailView(RetrieveUpdateAPIView):
    """API Endpoint for one Subscription object.

    The View does not include the Destroy (DELETE method) keyword, preventing
    to actually delete a Subscription instance. To *cancel* a subscription,
    one must change its "status" through an PUT method.

    AutoCreateCustomerMixin is NOT included, as it makes no real sense
    to create a non-existing Customer when accessing an existing Subscription
    object, which should have been gone through the ListAPIView first anyway.
    """

    queryset = Subscription.objects.all()
    permission_classes = (IsAuthenticated, IsSubscriptionOwner)
    serializer_class = SubscriptionSerializer


class PlanListView(ListAPIView):
    queryset = Plan.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = PlanSerializer


class PlanDetailView(RetrieveAPIView):
    queryset = Plan.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = PlanSerializer
