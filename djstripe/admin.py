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


class StripeObjectAdmin(admin.ModelAdmin):
    date_hierarchy = "stripe_timestamp"
    readonly_fields = [
        'stripe_id',
        'livemode',
        'stripe_timestamp',
    ]

    def get_fieldsets(self, request, obj=None):
        return (
            (None, {
                'fields': (
                    'stripe_id',
                    'livemode',
                    'stripe_timestamp',
                )
            }),
            (self.model.__name__, {
                'fields': self.get_fields(request, obj),
            }),
        )


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


@admin.register(Charge)
class ChargeAdmin(StripeObjectAdmin):
    list_display = [
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
    ]
    search_fields = [
        "stripe_id",
        "customer__stripe_id",
        "invoice__stripe_id",
    ]
    list_filter = [
        "paid",
        "disputed",
        "refunded",
        "stripe_timestamp",
    ]
    raw_id_fields = [
        "customer",
    ]
    fields = [
        "amount",
        "amount_refunded",
        "captured",
        "currency",
        "failure_code",
        "failure_message",
        "paid",
        "refunded",
        "shipping",
        "statement_descriptor",
        "status",
        "fee",
        "fee_details",
        "source_type",
        "source_stripe_id",
        "disputed",
        "fraudulent",
        "account",
        "customer",
        "transfer",
        "source",
    ]
    actions = [send_charge_receipt]


@admin.register(EventProcessingException)
class EventProcessingExceptionAdmin(admin.ModelAdmin):
    date_hierarchy = "created"
    list_display = [
        "message",
        "event",
        "created",
    ]
    search_fields = [
        "message",
        "traceback",
        "data",
    ]
    fields = [
        "event",
        "data",
        "message",
        "traceback",
    ]


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


@admin.register(Event)
class EventAdmin(StripeObjectAdmin):
    raw_id_fields = ["customer"]
    list_display = [
        "stripe_id",
        "type",
        "livemode",
        "valid",
        "processed",
        "stripe_timestamp",
    ]
    list_filter = [
        "type",
        "created",
        "valid",
        "processed",
    ]
    search_fields = [
        "stripe_id",
        "customer__stripe_id",
        "validated_message",
    ]
    actions = [reprocess_events]
    fields = [
        'type',
        'request_id',
        'received_api_version',
        'webhook_message',
        'customer',
        'valid',
        'processed',
    ]


class SubscriptionInline(admin.TabularInline):
    """A TabularInline for use models.Subscription."""
    model = Subscription
    extra = 0


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


@admin.register(Subscription)
class SubscriptionAdmin(StripeObjectAdmin):
    raw_id_fields = [
        "customer",
        "plan",
    ]
    list_display = [
        "stripe_id",
        "status",
        "stripe_timestamp",
    ]
    list_filter = [
        "status",
    ]
    search_fields = [
        "stripe_id",
    ]
    fields = [
        "application_fee_percent",
        "cancel_at_period_end",
        "canceled_at",
        "current_period_start",
        "current_period_end",
        "ended_at",
        "quantity",
        "start",
        "status",
        "tax_percent",
        "trial_end",
        "trial_start",
        "customer",
        "plan",
    ]
    actions = [cancel_subscription]


@admin.register(Customer)
class CustomerAdmin(StripeObjectAdmin):
    raw_id_fields = ["subscriber"]
    list_display = [
        "stripe_id",
        "subscriber",
        subscription_status,
        "stripe_timestamp"
    ]
    list_filter = [
        CustomerHasSourceListFilter,
        CustomerSubscriptionStatusListFilter
    ]
    search_fields = [
        "stripe_id"
    ]
    fields = [
        "account_balance",
        "business_vat_id",
        "currency",
        "delinquent",
        "shipping",
        "default_source",
        "subscriber",
        "date_purged",
    ]
    inlines = [SubscriptionInline]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super(CustomerAdmin, self).get_readonly_fields(request, obj))
        return readonly_fields + ["date_purged"]


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


@admin.register(Invoice)
class InvoiceAdmin(StripeObjectAdmin):
    raw_id_fields = ["customer"]
    list_display = [
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
        "stripe_timestamp",
    ]
    search_fields = [
        "stripe_id",
        "customer__stripe_id",
    ]
    list_filter = [
        InvoiceCustomerHasSourceListFilter,
        "paid",
        "forgiven",
        "closed",
        "attempted",
        "attempt_count",
        "stripe_timestamp",
        "date",
        "period_end",
        "total",
    ]
    fields = [
        "amount_due",
        "application_fee",
        "attempt_count",
        "attempted",
        "closed",
        "currency",
        "data",
        "ending_balance",
        "forgiven",
        "next_payment_attempt",
        "paid",
        "period_end",
        "period_start",
        "starting_balance",
        "statement_descriptor",
        "subscription_proration_date",
        "subtotal",
        "tax",
        "tax_percent",
        "total",
        "customer",
        "charge",
        "subscription",
    ]
    inlines = [InvoiceItemInline]


@admin.register(Transfer)
class TransferAdmin(StripeObjectAdmin):
    list_display = [
        "stripe_id",
        "amount",
        "status",
        "date",
        "description",
        "stripe_timestamp",
    ]
    search_fields = [
        "stripe_id",
    ]
    fields = [
        "amount",
        "amount_reversed",
        "currency",
        "date",
        "destination",
        "destination_payment",
        "destination_type",
        "failure_code",
        "failure_message",
        "reversed",
        "source_transaction",
        "source_type",
        "statement_descriptor",
        "status",
        "fee",
        "fee_details",
    ]


@admin.register(Plan)
class PlanAdmin(StripeObjectAdmin):
    """An Admin for use with models.Plan."""
    fields = [
        "amount",
        "currency",
        "interval",
        "interval_count",
        "name",
        "statement_descriptor",
        "trial_period_days",
    ]

    def save_model(self, request, obj, form, change):
        """Update or create objects using our custom methods that sync with Stripe."""
        if change:
            obj.update_name()

        else:
            Plan.get_or_create(**form.cleaned_data)

    def get_readonly_fields(self, request, obj=None):
        """Return extra readonly_fields."""
        readonly_fields = list(super(PlanAdmin, self).get_readonly_fields(request, obj))
        if obj:
            readonly_fields.extend([
                'amount',
                'currency',
                'interval',
                'interval_count',
                'trial_period_days'])

        return readonly_fields
