"""
dj-stripe - Views related to the djstripe app.
"""
import logging

from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from .models import WebhookEventTrigger

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class ProcessWebhookView(View):
    """
    A Stripe Webhook handler view.

    This will create a WebhookEventTrigger instance, verify it,
    then attempt to process it.

    If the webhook cannot be verified, returns HTTP 400.

    If an exception happens during processing, returns HTTP 500.
    """

    def post(self, request):
        if "HTTP_STRIPE_SIGNATURE" not in request.META:
            # Do not even attempt to process/store the event if there is
            # no signature in the headers so we avoid overfilling the db.
            logger.error("HTTP_STRIPE_SIGNATURE is missing")
            return HttpResponseBadRequest()

        trigger = WebhookEventTrigger.from_request(request)

        if trigger.is_test_event:
            # Since we don't do signature verification, we have to skip trigger.valid
            return HttpResponse("Test webhook successfully received and discarded!")

        if not trigger.valid:
            # Webhook Event did not validate, return 400
            logger.error("Trigger object did not validate")
            return HttpResponseBadRequest()

        return HttpResponse(str(trigger.id))
