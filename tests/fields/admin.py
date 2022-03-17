from django.contrib import admin

from djstripe.admin import StripeModelAdmin

from .models import TestCustomActionModel


@admin.register(TestCustomActionModel)
class TestCustomActionModelAdmin(StripeModelAdmin):

    # For Subscription model's custom action, _cancel
    def get_actions(self, request):
        # get all actions
        actions = super().get_actions(request)
        actions["_cancel"] = self.get_action("_cancel")
        return actions
