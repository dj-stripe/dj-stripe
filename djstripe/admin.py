# -*- coding: utf-8 -*-
"""
Note: Django 1.4 support was dropped in #107
        https://github.com/pydanny/dj-stripe/pull/107
"""

from django.contrib import admin

from .models import Event, EventProcessingException, Transfer, Charge, Plan
from .models import Invoice, InvoiceItem, CurrentSubscription, DJStripeCustomer


class CustomerHasCardListFilter(admin.SimpleListFilter):
    title = "card presence"
    parameter_name = "has_card"

    def lookups(self, request, model_admin):
        return [
            ["yes", "Has Card"],
            ["no", "Does Not Have a Card"]
        ]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(card_fingerprint="")
        if self.value() == "no":
            return queryset.filter(card_fingerprint="")


class InvoiceCustomerHasCardListFilter(admin.SimpleListFilter):
    title = "card presence"
    parameter_name = "has_card"

    def lookups(self, request, model_admin):
        return [
            ["yes", "Has Card"],
            ["no", "Does Not Have a Card"]
        ]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(djstripecustomer__card_fingerprint="")
        if self.value() == "no":
            return queryset.filter(djstripecustomer__card_fingerprint="")


class CustomerSubscriptionStatusListFilter(admin.SimpleListFilter):
    title = "subscription status"
    parameter_name = "sub_status"

    def lookups(self, request, model_admin):
        statuses = [
            [x, x.replace("_", " ").title()]
            for x in CurrentSubscription.objects.all().values_list(
                "status",
                flat=True
            ).distinct()
        ]
        statuses.append(["none", "No Subscription"])
        return statuses

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset.all()
        else:
            return queryset.filter(current_subscription__status=self.value())


def send_charge_receipt(modeladmin, request, queryset):
    """
    Function for sending receipts from the admin if a receipt is not sent for
    a specific charge.
    """
    for charge in queryset:
        charge.send_receipt()


admin.site.register(
    Charge,
    readonly_fields=('created',),
    list_display=[
        "stripe_id",
        "djstripecustomer",
        "amount",
        "description",
        "paid",
        "disputed",
        "refunded",
        "fee",
        "receipt_sent",
        "created"
    ],
    search_fields=[
        "stripe_id",
        "djstripecustomer__stripe_id",
        "djstripecustomer__customer__email",
        "card_last_4",
        "invoice__stripe_id"
    ],
    list_filter=[
        "paid",
        "disputed",
        "refunded",
        "card_kind",
        "created"
    ],
    raw_id_fields=[
        "djstripecustomer",
        "invoice"
    ],
    actions=(send_charge_receipt,),
)

admin.site.register(
    EventProcessingException,
    readonly_fields=('created',),
    list_display=[
        "message",
        "event",
        "created"
    ],
    search_fields=[
        "message",
        "traceback",
        "data"
    ],
)

admin.site.register(
    Event,
    raw_id_fields=["djstripecustomer"],
    readonly_fields=('created',),
    list_display=[
        "stripe_id",
        "kind",
        "livemode",
        "valid",
        "processed",
        "created"
    ],
    list_filter=[
        "kind",
        "created",
        "valid",
        "processed"
    ],
    search_fields=[
        "stripe_id",
        "djstripecustomer__stripe_id",
        "djstripecustomer__customer__email",
        "validated_message"
    ],
)


class CurrentSubscriptionInline(admin.TabularInline):
    model = CurrentSubscription


def subscription_status(obj):
    return obj.current_subscription.status
subscription_status.short_description = "Subscription Status"


admin.site.register(
    DJStripeCustomer,
    raw_id_fields=["customer"],
    readonly_fields=('created',),
    list_display=[
        "stripe_id",
        "customer",
        "card_kind",
        "card_last_4",
        subscription_status,
        "created"
    ],
    list_filter=[
        "card_kind",
        CustomerHasCardListFilter,
        CustomerSubscriptionStatusListFilter
    ],
    search_fields=[
        "stripe_id",
        "customer__email"
    ],
    inlines=[CurrentSubscriptionInline]
)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem


def djstripecustomer_has_card(obj):
    """ Returns True if the customer has a card attached to its account."""
    return obj.djstripecustomer.card_fingerprint != ""
djstripecustomer_has_card.short_description = "DJStripeCustomer Has Card"


def djstripecustomer_email(obj):
    """ Returns a string representation of the djstripe customer's email."""
    return str(obj.djstripecustomer.customer.email)
djstripecustomer_email.short_description = "DJStripeCustomer"


admin.site.register(
    Invoice,
    raw_id_fields=["djstripecustomer"],
    readonly_fields=('created',),
    list_display=[
        "stripe_id",
        "paid",
        "closed",
        djstripecustomer_email,
        djstripecustomer_has_card,
        "period_start",
        "period_end",
        "subtotal",
        "total",
        "created"
    ],
    search_fields=[
        "stripe_id",
        "djstripecustomer__stripe_id",
        "djstripecustomer__customer__email"
    ],
    list_filter=[
        InvoiceCustomerHasCardListFilter,
        "paid",
        "closed",
        "attempted",
        "attempts",
        "created",
        "date",
        "period_end",
        "total"
    ],
    inlines=[InvoiceItemInline]
)


admin.site.register(
    Transfer,
    raw_id_fields=["event"],
    readonly_fields=('created',),
    list_display=[
        "stripe_id",
        "amount",
        "status",
        "date",
        "description",
        "created"
    ],
    search_fields=[
        "stripe_id",
        "event__stripe_id"
    ]
)


class PlanAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):
        """Update or create objects using our custom methods that
        sync with Stripe."""

        if change:
            obj.update_name()

        else:
            Plan.get_or_create(**form.cleaned_data)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj:
            readonly_fields.extend([
                'stripe_id',
                'amount',
                'currency',
                'interval',
                'interval_count',
                'trial_period_days'])

        return readonly_fields

admin.site.register(Plan, PlanAdmin)
