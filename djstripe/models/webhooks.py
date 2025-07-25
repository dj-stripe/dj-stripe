"""
Module for dj-stripe Webhook models
"""

import json
import warnings
from traceback import format_exc
from uuid import uuid4

import stripe
from django.conf import settings
from django.db import models
from django.utils.datastructures import CaseInsensitiveMapping
from django.utils.functional import cached_property

from .. import signals
from ..enums import WebhookEndpointStatus, WebhookEndpointValidation
from ..fields import JSONField, StripeEnumField, StripeForeignKey
from ..settings import djstripe_settings
from .base import StripeModel, logger
from .core import Event


# TODO: Add Tests
class WebhookEndpoint(StripeModel):
    stripe_class = stripe.WebhookEndpoint
    stripe_dashboard_item_name = "webhooks"

    api_version = models.CharField(
        max_length=64,
        blank=True,
        help_text=(
            "The API version events are rendered as for this webhook endpoint. Defaults"
            " to the configured Stripe API Version."
        ),
    )
    enabled_events = JSONField(
        help_text=(
            "The list of events to enable for this endpoint. ['*'] indicates that all"
            " events are enabled, except those that require explicit selection."
        )
    )
    secret = models.CharField(
        max_length=256,
        blank=True,
        editable=False,
        help_text="The endpoint's secret, used to generate webhook signatures.",
    )
    status = StripeEnumField(
        enum=WebhookEndpointStatus,
        help_text="The status of the webhook. It can be enabled or disabled.",
    )
    url = models.URLField(help_text="The URL of the webhook endpoint.", max_length=2048)
    application = models.CharField(
        max_length=255,
        blank=True,
        help_text="The ID of the associated Connect application.",
    )

    djstripe_uuid = models.UUIDField(
        unique=True,
        default=uuid4,
        help_text="A UUID specific to dj-stripe generated for the endpoint",
    )
    djstripe_tolerance = models.PositiveSmallIntegerField(
        help_text=(
            "Controls the milliseconds tolerance which wards against replay attacks."
            " Leave this to its default value unless you know what you're doing."
        ),
        default=stripe.Webhook.DEFAULT_TOLERANCE,
    )
    djstripe_validation_method = StripeEnumField(
        enum=WebhookEndpointValidation,
        help_text="Controls the webhook validation method.",
        default=WebhookEndpointValidation.verify_signature,
    )

    def __str__(self):
        return self.url or str(self.djstripe_uuid)

    def _attach_objects_hook(
        self, cls, data, current_ids=None, api_key=djstripe_settings.STRIPE_SECRET_KEY
    ):
        """
        Gets called by this object's create and sync methods just before save.
        Use this to populate fields before the model is saved.
        """
        super()._attach_objects_hook(
            cls, data, current_ids=current_ids, api_key=api_key
        )
        self.djstripe_uuid = data.get("metadata", {}).get("djstripe_uuid")

        djstripe_tolerance = data.get("djstripe_tolerance")
        # As djstripe_tolerance can be set to 0
        if djstripe_tolerance is not None:
            self.djstripe_tolerance = djstripe_tolerance

        djstripe_validation_method = data.get("djstripe_validation_method")
        if djstripe_validation_method:
            self.djstripe_validation_method = djstripe_validation_method


def _get_version():
    from ..apps import __version__

    return __version__


def get_remote_ip(request):
    """Given the HTTPRequest object return the IP Address of the client

    :param request: client request
    :type request: HTTPRequest

    :Returns: the client ip address
    """

    # x-forwarded-for is relevant for django running behind a proxy
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")

    if not ip:
        warnings.warn(
            "Could not determine remote IP (missing REMOTE_ADDR). "
            "This is likely an issue with your wsgi/server setup."
        )
        ip = "0.0.0.0"

    return ip


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
    webhook_endpoint = StripeForeignKey(
        "WebhookEndpoint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The endpoint this webhook was received on",
    )

    def __str__(self):
        return f"id={self.id}, valid={self.valid}, processed={self.processed}"

    @classmethod
    def from_request(cls, request, *, webhook_endpoint: WebhookEndpoint):
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

        ip = get_remote_ip(request)

        stripe_account = webhook_endpoint.djstripe_owner_account
        secret = webhook_endpoint.secret

        obj = cls.objects.create(
            headers=dict(request.headers),
            body=body,
            remote_ip=ip,
            stripe_trigger_account=stripe_account,
            webhook_endpoint=webhook_endpoint,
        )
        api_key = (
            stripe_account.default_api_key if stripe_account else None
        ) or djstripe_settings.get_default_api_key(webhook_endpoint.livemode)

        try:
            # Validate the webhook first
            signals.webhook_pre_validate.send(sender=cls, instance=obj)

            # Default to per Webhook Endpoint Tolerance
            obj.valid = obj.validate(
                secret=secret,
                api_key=api_key,
            )

            # send post webhook validate signal
            signals.webhook_post_validate.send(
                sender=cls, instance=obj, valid=obj.valid
            )

            if obj.valid:
                signals.webhook_pre_process.send(sender=cls, instance=obj)

                # todo this should be moved to per webhook endpoint callback
                if djstripe_settings.WEBHOOK_EVENT_CALLBACK:
                    # If WEBHOOK_EVENT_CALLBACK, pass it for processing
                    djstripe_settings.WEBHOOK_EVENT_CALLBACK(obj, api_key=api_key)
                else:
                    # Process the item (do not save it, it'll get saved below)
                    obj.process(save=False, api_key=api_key)
                signals.webhook_post_process.send(
                    sender=cls, instance=obj, api_key=api_key
                )
        except Exception as e:
            max_length = cls._meta.get_field("exception").max_length
            obj.exception = str(e)[:max_length]
            obj.traceback = format_exc()

            # Send the exception as the webhook_processing_error signal
            signals.webhook_processing_error.send(
                sender=cls,
                instance=obj,
                api_key=api_key,
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

    def verify_signature(self, secret: str, tolerance: int) -> bool:
        if not secret:
            raise ValueError("Cannot verify event signature without a secret")

        # HTTP headers are case-insensitive, but we store them as a dict.
        signature = CaseInsensitiveMapping(self.headers).get("stripe-signature")

        try:
            stripe.WebhookSignature.verify_header(
                self.body, signature, secret, tolerance
            )
        except stripe.error.SignatureVerificationError:
            logger.exception("Failed to verify header")
            return False
        else:
            return True

    def validate(
        self,
        api_key: str,
        secret: str,
    ):
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

        validation_method = self.webhook_endpoint.djstripe_validation_method

        if validation_method == WebhookEndpointValidation.none:
            # validation disabled
            warnings.warn("WEBHOOK VALIDATION is disabled.")
            return True
        elif validation_method == WebhookEndpointValidation.verify_signature:
            if settings.DEBUG:
                # In debug mode, allow overriding the webhook secret with
                # the x-djstripe-webhook-secret header.
                # (used for stripe cli webhook forwarding)
                headers = CaseInsensitiveMapping(self.headers)
                local_secret = headers.get("x-djstripe-webhook-secret")
                secret = local_secret or secret
            return self.verify_signature(
                secret=secret, tolerance=self.webhook_endpoint.djstripe_tolerance
            )

        livemode = local_data["livemode"]
        api_key = api_key or djstripe_settings.get_default_api_key(livemode)

        # Retrieve the event using the api_version specified in itself
        remote_data = Event.stripe_class.retrieve(
            id=local_data["id"],
            api_key=api_key,
            stripe_version=local_data["api_version"],
        )

        return local_data["data"] == remote_data["data"]

    def process(self, save=True, api_key: str | None = None):
        # Reset traceback and exception in case of reprocessing
        self.exception = ""
        self.traceback = ""

        self.event = Event.process(self.json_body, api_key=api_key)
        self.processed = True
        if save:
            self.save()

        return self.event
