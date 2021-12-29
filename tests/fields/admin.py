from django.contrib import admin

from djstripe.admin import StripeModelAdmin

from .models import TestCustomActionModel


@admin.register(TestCustomActionModel)
class TestCustomActionModelAdmin(StripeModelAdmin):
    pass
