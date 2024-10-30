from django.contrib import admin
from django.shortcuts import render

from djstripe.admin.admin import StripeModelAdmin
from djstripe.admin.forms import CustomActionForm

from .models import CustomActionModel


@admin.register(CustomActionModel)
class CustomActionModelAdmin(StripeModelAdmin):
    def get_actions(self, request):
        # get all actions
        actions = super().get_actions(request)

        # For Subscription model's custom action, _cancel
        actions["_cancel"] = self.get_action("_cancel")

        # For SubscriptionSchedule's custom action, _release_subscription_schedule
        actions["_release_subscription_schedule"] = self.get_action(
            "_release_subscription_schedule"
        )
        # For SubscriptionSchedule's custom action, _cancel_subscription_schedule
        actions["_cancel_subscription_schedule"] = self.get_action(
            "_cancel_subscription_schedule"
        )
        return actions

    @admin.action(description="Cancel selected subscriptions")
    def _cancel(self, request, queryset):
        """Cancel a subscription."""
        context = self.get_admin_action_context(queryset, "_cancel", CustomActionForm)
        return render(request, "djstripe/admin/confirm_action.html", context)

    @admin.display(description="Release Selected Subscription Schedules")
    def _release_subscription_schedule(self, request, queryset):
        """Release a SubscriptionSchedule."""
        context = self.get_admin_action_context(
            queryset, "_release_subscription_schedule", CustomActionForm
        )
        return render(request, "djstripe/admin/confirm_action.html", context)

    def _cancel_subscription_schedule(self, request, queryset):
        """Cancel a SubscriptionSchedule."""
        context = self.get_admin_action_context(
            queryset, "_cancel_subscription_schedule", CustomActionForm
        )
        return render(request, "djstripe/admin/confirm_action.html", context)
