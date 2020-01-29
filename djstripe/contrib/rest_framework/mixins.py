from rest_framework.serializers import ModelSerializer
from rest_framework.views import APIView

from ...models import Customer
from ...settings import STRIPE_LIVE_MODE, subscriber_request_callback


class AutoCreateCustomerMixin(APIView):
    """Small mixin that can be included in REST API Views.

    If included, it will automatically create a Customer instance
    for the authenticated user, if does not yet exist.
    """

    def dispatch(self, request, *args, **kwargs):
        """Automatically creates a Customer if it does not exists yet.

        The dispatch method is called after permissions and auth have been resolved,
        but before the actual get/create/update methods are called.
        """
        result = super().dispatch(request, *args, **kwargs)
        if not request.user.is_anonymous:
            Customer.objects.get_or_create(
                subscriber=subscriber_request_callback(self.request)
            )
        return result


class AutoCustomerModelSerializerMixin(ModelSerializer):
    """Small mixin to easily provide access to the relevant customer
    inside ModelSerializers.
    """

    @property
    def customer(self):
        subscriber = subscriber_request_callback(self.context.get("request"))
        try:
            customer = Customer.objects.get(
                subscriber=subscriber, livemode=STRIPE_LIVE_MODE
            )
        except Customer.DoesNotExist:
            return None
        else:
            return customer
