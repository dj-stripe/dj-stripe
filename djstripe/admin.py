# -*- coding: utf-8 -*-
"""
Note: Code to make this work with Django 1.5+ customer user models
        was inspired by work by Andrew Brown (@almostabc).
"""

from django.contrib import admin
from django.db.models.fields import FieldDoesNotExist

from .models import Event, EventProcessingException, Transfer, Charge, Plan
from .models import Invoice, InvoiceItem, CurrentSubscription, Customer

from .settings import User

if hasattr(User, 'USERNAME_FIELD'):
    # Using a Django 1.5 User model
    user_search_fields = [
        "customer__user__{0}".format(User.USERNAME_FIELD)
    ]

    try:
        # get_field_by_name throws FieldDoesNotExist if the field is not present on the model
        User._meta.get_field_by_name('email')
        user_search_fields + ["customer__user__email"]
    except FieldDoesNotExist:
        pass
else:
    # Using a pre-Django 1.5 User model
    user_search_fields = [
        "customer__user__username",
        "customer__user__email"
    ]


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
            return queryset.exclude(customer__card_fingerprint="")
        if self.value() == "no":
            return queryset.filter(customer__card_fingerprint="")


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
        "customer",
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
        "customer__stripe_id",
        "customer__user__email",
        "card_last_4",
        "customer__user__username",
        "invoice__stripe_id"
    ] + user_search_fields,
    list_filter=[
        "paid",
        "disputed",
        "refunded",
        "card_kind",
        "created"
    ],
    raw_id_fields=[
        "customer",
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
    raw_id_fields=["customer"],
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
        "customer__stripe_id",
        "customer__user__username",
        "customer__user__email",
        "validated_message"
    ] + user_search_fields,
)


class CurrentSubscriptionInline(admin.TabularInline):
    model = CurrentSubscription


def subscription_status(obj):
    return obj.current_subscription.status
subscription_status.short_description = "Subscription Status"


admin.site.register(
    Customer,
    raw_id_fields=["user"],
    readonly_fields=('created',),
    list_display=[
        "stripe_id",
        "user",
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
        "user__username",
        "user__email"
    ],
    inlines=[CurrentSubscriptionInline]
)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem


def customer_has_card(obj):
    return obj.customer.card_fingerprint != ""
customer_has_card.short_description = "Customer Has Card"


def customer_user(obj):
    if hasattr(obj, 'USERNAME_FIELD'):
        # Using a Django 1.5 User model
        username = getattr(obj.customer.user, User.USERNAME_FIELD)
    else:
        # Using a pre-Django 1.5 User model
        username = obj.customer.user.username
    # In Django 1.5+ a User is not guaranteed to have an email field
    email = getattr(obj.customer.user, 'email', '')

    return "{0} <{1}>".format(
        username,
        email
    )
customer_has_card.short_description = "Customer"


admin.site.register(
    Invoice,
    raw_id_fields=["customer"],
    readonly_fields=('created',),
    list_display=[
        "stripe_id",
        "paid",
        "closed",
        customer_user,
        customer_has_card,
        "period_start",
        "period_end",
        "subtotal",
        "total",
        "created"
    ],
    search_fields=[
        "stripe_id",
        "customer__stripe_id",
        "customer__user__username",
        "customer__user__email"
    ] + user_search_fields,
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
