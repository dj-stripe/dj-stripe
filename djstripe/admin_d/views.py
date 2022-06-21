"""
dj-stripe - Views related to the djstripe app.
"""
import logging

import stripe
from django.contrib import messages
from django.contrib.admin import helpers, site
from django.core.management import call_command
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import FormView

from djstripe import utils

from .forms import CustomActionForm

logger = logging.getLogger(__name__)


class ConfirmCustomAction(FormView):
    template_name = "djstripe/admin/confirm_action.html"
    form_class = CustomActionForm

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
