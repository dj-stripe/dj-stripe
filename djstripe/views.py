"""
dj-stripe - Views related to the djstripe app.
"""
import logging

import stripe
from django.contrib import messages
from django.contrib.admin import helpers, site
from django.core.management import call_command
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import iri_to_uri
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, View

from djstripe import utils
from djstripe.forms import CustomActionForm

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


class ConfirmCustomAction(FormView):
    template_name = "djstripe/admin/confirm_action.html"
    form_class = CustomActionForm

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_staff):
            return HttpResponseRedirect(
                reverse("admin:login") + f"?next={iri_to_uri(request.path_info)}"
            )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        model_name = self.kwargs.get("model_name")
        action_name = self.kwargs.get("action_name")
        model = utils.get_model(model_name)

        pks = form.cleaned_data.get(helpers.ACTION_CHECKBOX_NAME)

        # get the handler
        handler = getattr(self, action_name)

        if action_name == "_sync_all_instances":
            # Create Empty Queryset to be able to extract the model name
            # as sync all would sync all instances anyway and there is no guarantee
            # that the local db already has all the instances.
            qs = model.objects.none()
        else:
            qs = utils.get_queryset(pks, model_name)

        # Process Request
        handler(self.request, qs)

        return HttpResponseRedirect(
            reverse(
                f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
            )
        )

    def form_invalid(self, form):
        model_name = self.kwargs.get("model_name")
        action_name = self.kwargs.get("action_name")

        model = utils.get_model(model_name)
        pks = form.data.getlist(helpers.ACTION_CHECKBOX_NAME)
        pks = list(map(int, pks))

        queryset = utils.get_queryset(pks, model_name)

        model_admin = site._registry.get(model)
        for msg in form.errors.values():
            messages.add_message(self.request, messages.ERROR, msg.as_text())

        return model_admin.get_action(action_name)[0](
            model_admin, self.request, queryset
        )

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs["model_name"] = self.kwargs.get("model_name")
        form_kwargs["action_name"] = self.kwargs.get("action_name")
        return form_kwargs

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

    def _release_subscription_schedule(self, request, queryset):
        """Release a SubscriptionSchedule."""
        for subscription_schedule in queryset:
            try:
                instance = subscription_schedule.release()
                messages.success(request, f"Successfully Released: {instance}")
            except stripe.error.InvalidRequestError as error:
                messages.warning(request, error)

    def _cancel_subscription_schedule(self, request, queryset):
        """Cancel a SubscriptionSchedule."""
        for subscription_schedule in queryset:
            try:
                instance = subscription_schedule.cancel()
                messages.success(request, f"Successfully Canceled: {instance}")
            except stripe.error.InvalidRequestError as error:
                messages.warning(request, error)
