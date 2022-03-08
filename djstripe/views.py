"""
dj-stripe - Views related to the djstripe app.
"""
import logging

import stripe
from django.apps import apps
from django.contrib import messages
from django.contrib.admin.utils import quote
from django.core.management import call_command
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import iri_to_uri
from django.utils.html import format_html
from django.utils.text import capfirst
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from .models import WebhookEndpoint, WebhookEventTrigger

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

    def post(self, request, uuid=None):
        if "HTTP_STRIPE_SIGNATURE" not in request.META:
            # Do not even attempt to process/store the event if there is
            # no signature in the headers so we avoid overfilling the db.
            logger.error("HTTP_STRIPE_SIGNATURE is missing")
            return HttpResponseBadRequest()

        # uuid is passed for new-style webhook views only.
        # old-style defaults to no account.
        if uuid:
            # If the UUID is invalid (does not exist), this will throw a 404.
            # Note that this happens after the HTTP_STRIPE_SIGNATURE check on purpose.
            webhook_endpoint = get_object_or_404(WebhookEndpoint, djstripe_uuid=uuid)
        else:
            webhook_endpoint = None

        trigger = WebhookEventTrigger.from_request(
            request, webhook_endpoint=webhook_endpoint
        )

        if trigger.is_test_event:
            # Since we don't do signature verification, we have to skip trigger.valid
            return HttpResponse("Test webhook successfully received and discarded!")

        if not trigger.valid:
            # Webhook Event did not validate, return 400
            logger.error("Trigger object did not validate")
            return HttpResponseBadRequest()

        return HttpResponse(str(trigger.id))


class ConfirmCustomAction(View):
    template_name = "djstripe/admin/confirm_action.html"
    app_label = "djstripe"
    app_config = apps.get_app_config(app_label)

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_staff):
            return HttpResponseRedirect(
                reverse("admin:login") + f"?next={iri_to_uri(request.path_info)}"
            )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        model_name = self.kwargs.get("model_name")
        model = self.app_config.get_model(model_name)
        qs = self.get_queryset()

        # process the request
        handler = getattr(self, self.kwargs.get("action_name"))
        handler(request, qs)

        return HttpResponseRedirect(
            reverse(
                f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
            )
        )

    def get_queryset(self):
        model_name = self.kwargs.get("model_name")
        model_pks = self.kwargs.get("model_pks").split(",")
        model = self.app_config.get_model(model_name)
        if model_pks == ["all"]:
            return model.objects.all()
        return model.objects.filter(pk__in=model_pks)

    def get_context_data(self, **kwargs):
        context = {}

        # add action_name
        context["action_name"] = self.kwargs.get("action_name")

        qs = self.get_queryset()

        context["info"] = []
        for obj in qs:
            admin_url = reverse(
                f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
                None,
                (quote(obj.pk),),
            )
            context["info"].append(
                format_html(
                    '{}: <a href="{}">{}</a>',
                    capfirst(obj._meta.verbose_name),
                    admin_url,
                    obj,
                )
            )

        return context

    def _resync_instances(self, request, queryset):
        for instance in queryset:
            api_key = instance.default_api_key
            try:
                if instance.djstripe_owner_account:
                    stripe_data = instance.api_retrieve(
                        stripe_account=instance.djstripe_owner_account.id,
                        api_key=api_key,
                    )
                else:
                    stripe_data = instance.api_retrieve()
                instance.__class__.sync_from_stripe_data(stripe_data, api_key=api_key)
                messages.success(request, f"Successfully Synced: {instance}")
            except stripe.error.PermissionError as error:
                messages.warning(request, error)
            except stripe.error.InvalidRequestError:
                raise

    def _sync_all_instances(self, request, queryset):
        """Admin Action to Sync All Instances"""
        call_command("djstripe_sync_models", queryset.model.__name__)
        messages.success(request, "Successfully Synced All Instances")

    def _cancel(self, request, queryset):
        """Cancel a subscription."""
        for subscription in queryset:
            try:
                instance = subscription.cancel()
                messages.success(request, f"Successfully Canceled: {instance}")
            except stripe.error.InvalidRequestError as error:
                messages.warning(request, error)
