import json
import warnings
from traceback import format_exc

import stripe
from django.db import models
from django.utils.functional import cached_property

from .. import settings as djstripe_settings
from ..context_managers import stripe_temporary_api_version
from ..fields import JSONField
from ..signals import webhook_processing_error
from ..utils import fix_django_headers
from .base import logger
from .core import Event


def _get_version():
    from .. import __version__

    return __version__


class WebhookEventTrigger(models.Model):
    """
    An instance of a request that reached the server endpoint for Stripe webhooks.

    Webhook Events are initially **UNTRUSTED**, as it is possible for any web entity to
    post any data to our webhook url. Data posted may be valid Stripe information,
    garbage, or even malicious.
    The 'valid' flag in this model monitors this.
    """

    id = models.BigAutoField(primary_key=True)
    remote_ip = models.GenericIPAddressField(
        help_text="IP address of the request client."
    )
    headers = JSONField()
    body = models.TextField(blank=True)
    valid = models.BooleanField(
        default=False,
        help_text="Whether or not the webhook event has passed validation",
    )
    processed = models.BooleanField(
        default=False,
        help_text="Whether or not the webhook event has been successfully processed",
    )
    exception = models.CharField(max_length=128, blank=True)
    traceback = models.TextField(
        blank=True, help_text="Traceback if an exception was thrown during processing"
    )
    event = models.ForeignKey(
        "Event",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Event object contained in the (valid) Webhook",
    )
    djstripe_version = models.CharField(
        max_length=32,
        default=_get_version,  # Needs to be a callable, otherwise it's a db default.
        help_text="The version of dj-stripe when the webhook was received",
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    @classmethod
    def from_request(cls, request):
        """
        Create, validate and process a WebhookEventTrigger given a Django
        request object.

        The process is three-fold:
        1. Create a WebhookEventTrigger object from a Django request.
        2. Validate the WebhookEventTrigger as a Stripe event using the API.
        3. If valid, process it into an Event object (and child resource).
        """

        headers = fix_django_headers(request.META)
        assert headers
        try:
            body = request.body.decode(request.encoding or "utf-8")
        except Exception:
            body = "(error decoding body)"

        ip = request.META.get("REMOTE_ADDR")
        if not ip:
            warnings.warn(
                "Could not determine remote IP (missing REMOTE_ADDR). "
                "This is likely an issue with your wsgi/server setup."
            )
            ip = "0.0.0.0"
        obj = cls.objects.create(headers=headers, body=body, remote_ip=ip)

        try:
            obj.valid = obj.validate()
            if obj.valid:
                if djstripe_settings.WEBHOOK_EVENT_CALLBACK:
                    # If WEBHOOK_EVENT_CALLBACK, pass it for processing
                    djstripe_settings.WEBHOOK_EVENT_CALLBACK(obj)
                else:
                    # Process the item (do not save it, it'll get saved below)
                    obj.process(save=False)
        except Exception as e:
            max_length = WebhookEventTrigger._meta.get_field("exception").max_length
            obj.exception = str(e)[:max_length]
            obj.traceback = format_exc()

            # Send the exception as the webhook_processing_error signal
            webhook_processing_error.send(
                sender=WebhookEventTrigger,
                exception=e,
                data=getattr(e, "http_body", ""),
            )

            # re-raise the exception so Django sees it
            raise e
        finally:
            obj.save()

        return obj

    @cached_property
    def json_body(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    @property
    def is_test_event(self):
        event_id = self.json_body.get("id")
        return event_id and event_id.endswith("_00000000000000")

    def validate(self, api_key=None):
        """
        The original contents of the Event message must be confirmed by
        refetching it and comparing the fetched data with the original data.

        This function makes an API call to Stripe to redownload the Event data
        and returns whether or not it matches the WebhookEventTrigger data.
        """

        local_data = self.json_body
        if "id" not in local_data or "livemode" not in local_data:
            return False

        if self.is_test_event:
            logger.info("Test webhook received: {}".format(local_data))
            return False

        if djstripe_settings.WEBHOOK_VALIDATION is None:
            # validation disabled
            return True
        elif (
            djstripe_settings.WEBHOOK_VALIDATION == "verify_signature"
            and djstripe_settings.WEBHOOK_SECRET
        ):
            try:
                stripe.WebhookSignature.verify_header(
                    self.body,
                    self.headers.get("stripe-signature"),
                    djstripe_settings.WEBHOOK_SECRET,
                    djstripe_settings.WEBHOOK_TOLERANCE,
                )
            except stripe.error.SignatureVerificationError:
                return False
            else:
                return True

        livemode = local_data["livemode"]
        api_key = api_key or djstripe_settings.get_default_api_key(livemode)

        # Retrieve the event using the api_version specified in itself
        with stripe_temporary_api_version(local_data["api_version"], validate=False):
            remote_data = Event.stripe_class.retrieve(
                id=local_data["id"], api_key=api_key
            )

        return local_data["data"] == remote_data["data"]

    def process(self, save=True):
        # Reset traceback and exception in case of reprocessing
        self.exception = ""
        self.traceback = ""

        self.event = Event.process(self.json_body)
        self.processed = True
        if save:
            self.save()

        return self.event
