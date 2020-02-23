"""
.. module:: dj-stripe.contrib.rest_framework.views.

    :synopsis: Views for the dj-stripe REST API.

.. moduleauthor:: Philippe Luickx (@philippeluickx)

"""
import warnings

from rest_framework import status
from rest_framework.views import APIView

from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from ...enums import SubscriptionStatus
from ...models import Plan, Subscription, Customer
from ...settings import CANCELLATION_AT_PERIOD_END, subscriber_request_callback

from .mixins import AutoCreateCustomerMixin
from .permissions import IsSubscriptionOwner
from .serializers import (
    CreateSubscriptionSerializer,
    PlanSerializer,
    SubscriptionSerializer,
)


class SubscriptionRestView(APIView):
    """API Endpoints for the Subscription object."""

    permission_classes = (IsAuthenticated,)

    def get(self, request, **kwargs):
        """
        Return the customer's valid subscriptions.

        Returns with status code 200.
        """
        warnings.warn('This view is deprecated. Use the new REST endpoints instead.')

        customer, _created = Customer.get_or_create(
            subscriber=subscriber_request_callback(self.request)
        )

        serializer = SubscriptionSerializer(customer.subscription)
        return Response(serializer.data)

    def post(self, request, **kwargs):
        """
        Create a new current subscription for the user.

        Returns with status code 201.
        """
        warnings.warn('This view is deprecated. Use the new REST endpoints instead.')

        serializer = CreateSubscriptionSerializer(data=request.data)

        if serializer.is_valid():
            try:
                customer, _created = Customer.get_or_create(
                    subscriber=subscriber_request_callback(self.request)
                )
                customer.add_card(serializer.data["stripe_token"])
                charge_immediately = serializer.data.get("charge_immediately")
                if charge_immediately is None:
                    charge_immediately = True

                customer.subscribe(serializer.data["plan"], charge_immediately)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception:
                # TODO: Better error messages
                return Response(
                    "Something went wrong processing the payment.",
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, **kwargs):
        """
        Mark the customers current subscription as canceled.

        Returns with status code 204.
        """
        warnings.warn('This view is deprecated. Use the new REST endpoints instead.')

        try:
            customer, _created = Customer.get_or_create(
                subscriber=subscriber_request_callback(self.request)
            )
            customer.subscription.cancel(at_period_end=CANCELLATION_AT_PERIOD_END)

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            return Response(
                "Something went wrong cancelling the subscription.",
                status=status.HTTP_400_BAD_REQUEST,
            )


class SubscriptionListView(AutoCreateCustomerMixin, ListCreateAPIView):
    """API Endpoints for the Subscription object.

    See the serializer methods about how the creation of a Subscription is
    handled.
    """

    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method.upper() == "POST":
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

    The View does not include the Destroy (DELETE HTTP method) keyword, preventing
    to actually delete a Subscription instance. To *cancel* a subscription,
    one must change its "status" through PUT/PATCH methods (but see delete method
    implementation below).

    AutoCreateCustomerMixin is NOT included, as it makes no real sense
    to create a non-existing Customer when accessing an existing Subscription
    object, which should have been gone through the ListAPIView first anyway.
    """

    queryset = Subscription.objects.all()
    permission_classes = (IsAuthenticated, IsSubscriptionOwner)
    serializer_class = SubscriptionSerializer
    lookup_field = "id"

    def delete(self, request, *args, **kwargs):
        # To stick to Stripe way of doing, we must enable the DELETE method to cancel
        # a subscription. Bur the default implementation truly deletes the object.
        # Hence we override it here to simulate a partial update (PATCH).
        # See https://stackoverflow.com/a/21262262/707984 for explanations about
        # _mutable.
        mutable = request.data._mutable
        request.data._mutable = True
        request.data.update(status=SubscriptionStatus.canceled)
        request.data._mutable = mutable
        return self.partial_update(request, *args, **kwargs)


class PlanListView(ListAPIView):
    queryset = Plan.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = PlanSerializer


class PlanDetailView(RetrieveAPIView):
    queryset = Plan.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = PlanSerializer
    lookup_field = "id"
