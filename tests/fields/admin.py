from django.contrib import admin
from django.shortcuts import render

from djstripe.admin.admin import StripeModelAdmin
from djstripe.admin.forms import CustomActionForm

from .models import CustomActionModel


@admin.register(CustomActionModel)
class CustomActionModelAdmin(StripeModelAdmin):
    actions = (
        *StripeModelAdmin.actions,
        # Subscription's custom action
        "_cancel",
        # SubscriptionSchedule's custom actions
        "_release_subscription_schedule",
        "_cancel_subscription_schedule",
    )

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
