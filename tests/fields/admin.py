from django.contrib import admin
from django.shortcuts import render

from djstripe.admin import StripeModelAdmin
from djstripe.forms import CustomActionForm

from .models import TestCustomActionModel


@admin.register(TestCustomActionModel)
class TestCustomActionModelAdmin(StripeModelAdmin):

    # For Subscription model's custom action, _cancel
    def get_actions(self, request):
        # get all actions
        actions = super().get_actions(request)
        actions["_cancel"] = self.get_action("_cancel")
        return actions

    @admin.action(description="Cancel selected subscriptions")
    def _cancel(self, request, queryset):
        """Cancel a subscription."""
        context = self.get_admin_action_context(queryset, "_cancel", CustomActionForm)
        return render(request, "djstripe/admin/confirm_action.html", context)
