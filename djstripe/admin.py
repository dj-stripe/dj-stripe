"""
Note: Code to make this work with Django 1.5+ customer user models
        was inspired by work by Andrew Brown (@almostabc).
"""

from django.contrib import admin
from django.db.models.fields import FieldDoesNotExist

from .models import Event, EventProcessingException, Transfer, Charge
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


admin.site.register(
    Charge,
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
)

admin.site.register(
    EventProcessingException,
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
    list_display=[
        "stripe_id",
        "user",
        "card_kind",
        "card_last_4",
        subscription_status
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
    ] + user_search_fields,
    inlines=[CurrentSubscriptionInline]
)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem


def customer_has_card(obj):
    return obj.customer.card_fingerprint != ""
customer_has_card.short_description = "Customer Has Card"


def customer_user(obj):
    if hasattr(User, 'USERNAME_FIELD'):
        # Using a Django 1.5 User model
        username = getattr(obj, obj.USERNAME_FIELD)
    else:
        # Using a pre-Django 1.5 User model
        username = obj.customer.user.username
    # In Django 1.5+ a User is not guaranteed to have an email field
    email = getattr(obj, 'email', '')

    return "{0} <{1}>".format(
        username,
        email
    )
customer_has_card.short_description = "Customer"


admin.site.register(
    Invoice,
    raw_id_fields=["customer"],
    list_display=[
        "stripe_id",
        "paid",
        "closed",
        customer_user,
        customer_has_card,
        "period_start",
        "period_end",
        "subtotal",
        "total"
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
    list_display=[
        "stripe_id",
        "amount",
        "status",
        "date",
        "description"
    ],
    search_fields=[
        "stripe_id",
        "event__stripe_id"
    ]
)