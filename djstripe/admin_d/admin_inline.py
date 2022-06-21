"""
Django Administration Inline interface definitions
"""
from django.contrib import admin

from djstripe import models

from .utils import get_forward_relation_fields_for_model


class SubscriptionInline(admin.StackedInline):
    """A TabularInline for use models.Subscription."""

    model = models.Subscription
    extra = 0
    readonly_fields = ("id", "created", "djstripe_owner_account")
    raw_id_fields = get_forward_relation_fields_for_model(model)
    show_change_link = True


class SubscriptionScheduleInline(admin.StackedInline):
    """A TabularInline for use models.SubscriptionSchedule."""

    model = models.SubscriptionSchedule
    extra = 0
    readonly_fields = ("id", "created", "djstripe_owner_account")
    raw_id_fields = get_forward_relation_fields_for_model(model)
    show_change_link = True

    def __init__(self, parent_model, admin_site):
        super().__init__(parent_model, admin_site)

        # dynamically set fk_name as SubscriptionScheduleInline is used
        # in CustomerAdmin as well as SubscriptionAdmin
        if parent_model is models.Subscription:
            self.fk_name = "subscription"


class TaxIdInline(admin.TabularInline):
    """A TabularInline for use models.Subscription."""

    model = models.TaxId
    extra = 0
    max_num = 5
    readonly_fields = (
        "id",
        "created",
        "verification",
        "livemode",
        "country",
        "djstripe_owner_account",
    )
    show_change_link = True


class SubscriptionItemInline(admin.StackedInline):
    """A TabularInline for use models.Subscription."""

    model = models.SubscriptionItem
    extra = 0
    readonly_fields = ("id", "created", "djstripe_owner_account")
    raw_id_fields = get_forward_relation_fields_for_model(model)
    show_change_link = True


class InvoiceItemInline(admin.StackedInline):
    """A TabularInline for use InvoiceItem."""

    model = models.InvoiceItem
    extra = 0
    readonly_fields = ("id", "created", "djstripe_owner_account")
    raw_id_fields = get_forward_relation_fields_for_model(model)
    show_change_link = True
