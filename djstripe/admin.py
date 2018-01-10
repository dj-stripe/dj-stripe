"""
.. module:: djstripe.admin.

   :synopsis: dj-stripe - Django Administration interface definitions

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib import admin

from .models import (
    Charge, Coupon, Customer, Dispute, Event, IdempotencyKey, Invoice,
    InvoiceItem, Plan, Source, Subscription, Transfer, WebhookEventTrigger
)


class BaseHasSourceListFilter(admin.SimpleListFilter):
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
        return (
            ("yes", "Has a source"),
            ("no", "Has no source"),
        )

    def queryset(self, request, queryset):
        """
        Return the filtered queryset based on the value provided in the query string.

        source: https://docs.djangoproject.com/en/1.10/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
        """
        filter_args = {self._filter_arg_key: None}

        if self.value() == "yes":
            return queryset.exclude(**filter_args)
        if self.value() == "no":
            return queryset.filter(**filter_args)


class CustomerHasSourceListFilter(BaseHasSourceListFilter):
    _filter_arg_key = "default_source"


class InvoiceCustomerHasSourceListFilter(BaseHasSourceListFilter):
    _filter_arg_key = "customer__default_source"


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
            for x in Subscription.objects.values_list(
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


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ("uuid", "action", "created", "is_expired", "livemode")
    list_filter = ("livemode", )
    search_fields = ("uuid", "action")


@admin.register(WebhookEventTrigger)
class WebhookEventTriggerAdmin(admin.ModelAdmin):
    list_display = (
        "created", "event", "remote_ip", "processed", "valid", "exception", "djstripe_version"
    )
    list_filter = ("created", "valid", "processed")
    raw_id_fields = ("event", )

    def reprocess(self, request, queryset):
        for trigger in queryset:
            if not trigger.valid:
                self.message_user(request, "Skipped invalid trigger {}".format(trigger))
                continue

            trigger.process()


class StripeObjectAdmin(admin.ModelAdmin):
    """Base class for all StripeObject-based model admins"""

    change_form_template = "djstripe/admin/change_form.html"

    def get_list_display(self, request):
        return ("stripe_id", ) + self.list_display + ("created", "livemode")

    def get_list_filter(self, request):
        return self.list_filter + ("created", "livemode")

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + ("stripe_id", "created")

    def get_search_fields(self, request):
        return self.search_fields + ("stripe_id", )

    def get_fieldsets(self, request, obj=None):
        common_fields = ("livemode", "stripe_id", "created")
        # Have to remove the fields from the common set, otherwise they'll show up twice.
        fields = [f for f in self.get_fields(request, obj) if f not in common_fields]
        return (
            (None, {"fields": common_fields}),
            (self.model.__name__, {"fields": fields}),
        )


class SubscriptionInline(admin.StackedInline):
    """A TabularInline for use models.Subscription."""

    model = Subscription
    extra = 0
    readonly_fields = ("stripe_id", "created")
    show_change_link = True


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


class InvoiceItemInline(admin.StackedInline):
    """A TabularInline for use InvoiceItem."""

    model = InvoiceItem
    extra = 0
    readonly_fields = ("stripe_id", "created")
    raw_id_fields = ("customer", "subscription")
    show_change_link = True


def customer_has_source(obj):
    """Return True if the customer has a source attached to its account."""
    return obj.customer.default_source is not None


customer_has_source.short_description = "Customer Has Source"


def customer_email(obj):
    """Return a string representation of the customer's email."""
    if obj.customer.subscriber:
        return str(obj.customer.subscriber.email)
    else:
        return ""


customer_email.short_description = "Customer"


@admin.register(Charge)
class ChargeAdmin(StripeObjectAdmin):
    list_display = (
        "customer", "amount", "description", "paid", "disputed", "refunded",
        "fee", "receipt_sent"
    )
    search_fields = ("stripe_id", "customer__stripe_id", "invoice__stripe_id")
    list_filter = (
        "status", "source_type", "paid", "refunded", "fraudulent", "captured",
    )
    raw_id_fields = ("customer", "dispute", "invoice", "source", "transfer")


@admin.register(Coupon)
class CouponAdmin(StripeObjectAdmin):
    list_display = (
        "amount_off", "percent_off", "duration", "duration_in_months",
        "redeem_by", "max_redemptions", "times_redeemed"
    )
    list_filter = ("duration", "redeem_by")
    radio_fields = {"duration": admin.HORIZONTAL}


@admin.register(Customer)
class CustomerAdmin(StripeObjectAdmin):
    raw_id_fields = ("subscriber", "default_source", "coupon")
    list_display = ("subscriber", subscription_status)
    list_filter = (CustomerHasSourceListFilter, CustomerSubscriptionStatusListFilter)
    inlines = (SubscriptionInline, )


@admin.register(Dispute)
class DisputeAdmin(StripeObjectAdmin):
    list_display = ("reason", "status", "amount", "currency", "is_charge_refundable")
    list_filter = ("is_charge_refundable", "reason", "status")


@admin.register(Event)
class EventAdmin(StripeObjectAdmin):
    list_display = ("type", "created", "request_id")
    list_filter = ("type", "created")
    search_fields = ("request_id", )

    def has_add_permission(self, request):
        return False


@admin.register(Invoice)
class InvoiceAdmin(StripeObjectAdmin):
    list_display = (
        "paid", "forgiven", "closed", customer_email, customer_has_source,
        "period_start", "period_end", "subtotal", "total"
    )
    list_filter = (
        InvoiceCustomerHasSourceListFilter, "paid", "forgiven", "closed", "attempted",
        "date", "period_end",
    )
    raw_id_fields = ("customer", "charge", "subscription")
    search_fields = ("customer__stripe_id", )
    inlines = (InvoiceItemInline, )


@admin.register(Plan)
class PlanAdmin(StripeObjectAdmin):
    radio_fields = {"interval": admin.HORIZONTAL}

    def save_model(self, request, obj, form, change):
        """Update or create objects using our custom methods that sync with Stripe."""
        if change:
            obj.update_name()
        else:
            Plan.get_or_create(**form.cleaned_data)

    def get_readonly_fields(self, request, obj=None):
        """Return extra readonly_fields."""
        readonly_fields = super(PlanAdmin, self).get_readonly_fields(request, obj)

        if obj:
            readonly_fields += (
                "amount", "currency", "interval", "interval_count", "trial_period_days"
            )

        return readonly_fields


@admin.register(Source)
class SourceAdmin(StripeObjectAdmin):
    raw_id_fields = ("customer", )
    list_display = ("customer", "type", "status", "amount", "currency", "usage", "flow")
    list_filter = ("type", "status", "usage", "flow")


@admin.register(Subscription)
class SubscriptionAdmin(StripeObjectAdmin):
    raw_id_fields = ("customer", )
    list_display = ("customer", "status")
    list_filter = ("status", "cancel_at_period_end")
    actions = (cancel_subscription, )


@admin.register(Transfer)
class TransferAdmin(StripeObjectAdmin):
    list_display = ("amount", "status", "date", "description")
