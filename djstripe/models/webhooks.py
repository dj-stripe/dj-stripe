"""
Module for dj-stripe Webhook models
"""

import json
import warnings
from traceback import format_exc

import stripe
from django.db import models
from django.utils.datastructures import CaseInsensitiveMapping
from django.utils.functional import cached_property

from ..context_managers import stripe_temporary_api_version
from ..fields import JSONField, StripeForeignKey
from ..settings import djstripe_settings
from ..signals import webhook_processing_error
from .base import StripeModel, logger
from .core import Event


def _get_version():
    from ..apps import __version__

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
    event = StripeForeignKey(
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
    stripe_trigger_account = StripeForeignKey(
        "djstripe.Account",
        on_delete=models.CASCADE,
        to_field="id",
        null=True,
        blank=True,
        help_text="The Stripe Account this object belongs to.",
    )

    def __str__(self):
        return f"id={self.id}, valid={self.valid}, processed={self.processed}"

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

        try:
            data = json.loads(body)
        except ValueError:
            data = {}

        obj = cls.objects.create(
            headers=dict(request.headers),
            body=body,
            remote_ip=ip,
            stripe_trigger_account=StripeModel._find_owner_account(data=data),
        )

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
            logger.error(
                '"id" not in json body or "livemode" not in json body(%s)', local_data
            )
            return False

        if self.is_test_event:
            logger.info("Test webhook received and discarded: {}".format(local_data))
            return False

        if djstripe_settings.WEBHOOK_VALIDATION is None:
            # validation disabled
            warnings.warn("WEBHOOK VALIDATION is disabled.")
            return True
        elif (
            djstripe_settings.WEBHOOK_VALIDATION == "verify_signature"
            and djstripe_settings.WEBHOOK_SECRET
        ):
            # HTTP headers are case-insensitive, but we store them as a dict.
            headers = CaseInsensitiveMapping(self.headers)
            try:
                stripe.WebhookSignature.verify_header(
                    self.body,
                    headers.get("stripe-signature"),
                    djstripe_settings.WEBHOOK_SECRET,
                    djstripe_settings.WEBHOOK_TOLERANCE,
                )
            except stripe.error.SignatureVerificationError:
                logger.exception("Failed to verify header")
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
