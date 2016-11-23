# -*- coding: utf-8 -*-
"""
.. module:: djstripe.admin.

   :synopsis: dj-stripe - Django Administration interface definitions

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

"""

from django.contrib import admin

from .models import Event, EventProcessingException, Transfer, Charge, Plan
from .models import Invoice, InvoiceItem, Subscription, Customer


class CustomerHasSourceListFilter(admin.SimpleListFilter):
    """A SimpleListFilter used with Customer admin."""

    title = "source presence"
    parameter_name = "has_source"

    def lookups(self, request, model_admin):
        """
        Return a list of tuples.

        The first element in each tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        source: https://docs.djangoproject.com/en/1.10/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
        """
        return [
            ["yes", "Has Source"],
            ["no", "Does Not Have Source"]
        ]

    def queryset(self, request, queryset):
        """
        Return the filtered queryset based on the value provided in the query string.

        source: https://docs.djangoproject.com/en/1.10/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
        """
        if self.value() == "yes":
            return queryset.exclude(default_source=None)
        if self.value() == "no":
            return queryset.filter(default_source=None)


class InvoiceCustomerHasSourceListFilter(admin.SimpleListFilter):
    """A SimpleListFilter used with Invoice admin."""

    title = "source presence"
    parameter_name = "has_source"

    def lookups(self, request, model_admin):
        """
        Return a list of tuples.

        The first element in each tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        source: https://docs.djangoproject.com/en/1.10/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
        """
        return [
            ["yes", "Has Source"],
            ["no", "Does Not Have Source"]
        ]

    def queryset(self, request, queryset):
        """
        Return the filtered queryset based on the value provided in the query string.

        source: https://docs.djangoproject.com/en/1.10/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
        """
        if self.value() == "yes":
            return queryset.exclude(customer__default_source=None)
        if self.value() == "no":
            return queryset.filter(customer__default_source=None)


class CustomerSubscriptionStatusListFilter(admin.SimpleListFilter):
    """A SimpleListFilter used with Customer admin."""

    title = "subscription status"
    parameter_name = "sub_status"

    def lookups(self, request, model_admin):
        """
        Return a list of tuples.

        The first element in each tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        source: https://docs.djangoproject.com/en/1.10/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
        """
        statuses = [
            [x, x.replace("_", " ").title()]
            for x in Subscription.objects.all().values_list(
                "status",
                flat=True
            ).distinct()
        ]
        statuses.append(["none", "No Subscription"])
        return statuses

    def queryset(self, request, queryset):
        """
        Return the filtered queryset based on the value provided in the query string.

        source: https://docs.djangoproject.com/en/1.10/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
        """
        if self.value() is None:
            return queryset.all()
        else:
            return queryset.filter(subscriptions__status=self.value()).distinct()


def send_charge_receipt(modeladmin, request, queryset):
    """Function for sending receipts from the admin if a receipt is not sent for a specific charge."""
    for charge in queryset:
        charge.send_receipt()


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
        "stripe_timestamp",
    ],
    search_fields=[
        "stripe_id",
        "customer__stripe_id",
        "invoice__stripe_id",
    ],
    list_filter=[
        "paid",
        "disputed",
        "refunded",
        "stripe_timestamp",
    ],
    raw_id_fields=[
        "customer",
    ],
    actions=(send_charge_receipt,),
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


def reprocess_events(modeladmin, request, queryset):
    """Re-process the selected webhook events.

    Note that this isn't idempotent, so any side-effects that are produced from
    the event being handled will be multiplied (for example, an event handler
    that sends emails will send duplicates; an event handler that adds 1 to a
    total count will be a count higher than it was, etc.)

    There aren't any event handlers with adverse side-effects built within
    dj-stripe, but there might be within your own event handlers, third-party
    plugins, contrib code, etc.
    """
    processed = 0
    for event in queryset:
        if event.process(force=True):
            processed += 1

    modeladmin.message_user(
        request,
        "{processed}/{total} event(s) successfully re-processed.".format(
            processed=processed, total=queryset.count()))


reprocess_events.short_description = "Re-process selected webhook events"


admin.site.register(
    Event,
    raw_id_fields=["customer"],
    list_display=[
        "stripe_id",
        "type",
        "livemode",
        "valid",
        "processed",
        "stripe_timestamp"
    ],
    list_filter=[
        "type",
        "created",
        "valid",
        "processed"
    ],
    search_fields=[
        "stripe_id",
        "customer__stripe_id",
        "validated_message"
    ],
    actions=[
        reprocess_events
    ],
)


class SubscriptionInline(admin.TabularInline):
    """A TabularInline for use models.Subscription."""

    model = Subscription


def subscription_status(customer):
    """
    Return a string representation of the customer's subscription status.

    If the customer does not have a subscription, an empty string is returned.
    """
    if customer.subscription:
        return customer.subscription.status
    else:
        return ""


subscription_status.short_description = "Subscription Status"


def cancel_subscription(modeladmin, request, queryset):
    """Cancel a subscription."""
    for subscription in queryset:
        subscription.cancel()


cancel_subscription.short_description = "Cancel selected subscriptions"

admin.site.register(
    Subscription,
    raw_id_fields=[
        "customer",
        "plan",
    ],
    list_display=[
        "stripe_id",
        "status",
        "stripe_timestamp",
    ],
    list_filter=[
        "status",
    ],
    search_fields=[
        "stripe_id",
    ],
    actions=[cancel_subscription]
)


admin.site.register(
    Customer,
    raw_id_fields=["subscriber"],
    list_display=[
        "stripe_id",
        "subscriber",
        subscription_status,
        "stripe_timestamp"
    ],
    list_filter=[
        CustomerHasSourceListFilter,
        CustomerSubscriptionStatusListFilter
    ],
    search_fields=[
        "stripe_id"
    ],
    inlines=[SubscriptionInline]
)


class InvoiceItemInline(admin.TabularInline):
    """A TabularInline for use models.InvoiceItem."""

    model = InvoiceItem


def customer_has_source(obj):
    """Return True if the customer has a source attached to its account."""
    return obj.customer.default_source is not None


customer_has_source.short_description = "Customer Has Source"


def customer_email(obj):
    """Return a string representation of the customer's email."""
    return str(obj.customer.subscriber.email)


customer_email.short_description = "Customer"


admin.site.register(
    Invoice,
    raw_id_fields=["customer"],
    readonly_fields=('stripe_timestamp',),
    list_display=[
        "stripe_id",
        "paid",
        "forgiven",
        "closed",
        customer_email,
        customer_has_source,
        "period_start",
        "period_end",
        "subtotal",
        "total",
        "stripe_timestamp"
    ],
    search_fields=[
        "stripe_id",
        "customer__stripe_id"
    ],
    list_filter=[
        InvoiceCustomerHasSourceListFilter,
        "paid",
        "forgiven",
        "closed",
        "attempted",
        "attempt_count",
        "stripe_timestamp",
        "date",
        "period_end",
        "total"
    ],
    inlines=[InvoiceItemInline]
)


admin.site.register(
    Transfer,
    list_display=[
        "stripe_id",
        "amount",
        "status",
        "date",
        "description",
        "stripe_timestamp"
    ],
    search_fields=[
        "stripe_id",
    ]
)


class PlanAdmin(admin.ModelAdmin):
    """An Admin for use with models.Plan."""

    def save_model(self, request, obj, form, change):
        """Update or create objects using our custom methods that sync with Stripe."""
        if change:
            obj.update_name()

        else:
            Plan.get_or_create(**form.cleaned_data)

    def get_readonly_fields(self, request, obj=None):
        """Return extra readonly_fields."""
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
