"""
Django Administration interface definitions
"""
from django.contrib import admin

from . import models


class ReadOnlyMixin:
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


def get_forward_relation_fields_for_model(model):
    """Return an iterable of the field names that are forward relations,
    I.E ManyToManyField, OneToOneField, and ForeignKey.

    Useful for perhaps ensuring the admin is always using raw ID fields for
    newly added forward relation fields.
    """
    return [
        field.name
        for field in model._meta.get_fields()
        # Get only relation fields
        if field.is_relation
        # Exclude auto relation fields, like reverse one to one.
        and not field.auto_created
        # We only want forward relations.
        and any((field.many_to_many, field.one_to_one, field.many_to_one))
    ]


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
        source:
        https://docs.djangoproject.com/en/1.10/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
        """
        return (("yes", "Has a source"), ("no", "Has no source"))

    def queryset(self, request, queryset):
        """
        Return the filtered queryset based on the value provided in the query string.

        source:
        https://docs.djangoproject.com/en/1.10/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
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
        source:
        https://docs.djangoproject.com/en/1.10/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
        """
        statuses = [
            [x, x.replace("_", " ").title()]
            for x in models.Subscription.objects.values_list(
                "status", flat=True
            ).distinct()
        ]
        statuses.append(["none", "No Subscription"])
        return statuses

    def queryset(self, request, queryset):
        """
        Return the filtered queryset based on the value provided in the query string.

        source:
        https://docs.djangoproject.com/en/1.10/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter
        """
        if self.value() is None:
            return queryset.all()
        else:
            return queryset.filter(subscriptions__status=self.value()).distinct()


@admin.register(models.IdempotencyKey)
class IdempotencyKeyAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = ("uuid", "action", "created", "is_expired", "livemode")
    list_filter = ("livemode",)
    search_fields = ("uuid", "action")


@admin.register(models.WebhookEventTrigger)
class WebhookEventTriggerAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = (
        "created",
        "event",
        "remote_ip",
        "processed",
        "valid",
        "exception",
        "djstripe_version",
    )
    list_filter = ("created", "valid", "processed")
    list_select_related = ("event",)
    raw_id_fields = get_forward_relation_fields_for_model(models.WebhookEventTrigger)

    def reprocess(self, request, queryset):
        for trigger in queryset:
            if not trigger.valid:
                self.message_user(request, "Skipped invalid trigger {}".format(trigger))
                continue

            trigger.process()


class StripeModelAdmin(admin.ModelAdmin):
    """Base class for all StripeModel-based model admins"""

    change_form_template = "djstripe/admin/change_form.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.raw_id_fields = get_forward_relation_fields_for_model(self.model)

    def get_list_display(self, request):
        return ("__str__", "id") + self.list_display + ("created", "livemode")

    def get_list_filter(self, request):
        return self.list_filter + ("created", "livemode")

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + ("id", "created")

    def get_search_fields(self, request):
        return self.search_fields + ("id",)

    def get_fieldsets(self, request, obj=None):
        common_fields = ("livemode", "id", "created")
        # Have to remove the fields from the common set,
        # otherwise they'll show up twice.
        fields = [f for f in self.get_fields(request, obj) if f not in common_fields]
        return (
            (None, {"fields": common_fields}),
            (self.model.__name__, {"fields": fields}),
        )


class SubscriptionInline(admin.StackedInline):
    """A TabularInline for use models.Subscription."""

    model = models.Subscription
    extra = 0
    readonly_fields = ("id", "created")
    raw_id_fields = get_forward_relation_fields_for_model(model)
    show_change_link = True


class SubscriptionItemInline(admin.StackedInline):
    """A TabularInline for use models.Subscription."""

    model = models.SubscriptionItem
    extra = 0
    readonly_fields = ("id", "created")
    raw_id_fields = get_forward_relation_fields_for_model(model)
    show_change_link = True


class InvoiceItemInline(admin.StackedInline):
    """A TabularInline for use InvoiceItem."""

    model = models.InvoiceItem
    extra = 0
    readonly_fields = ("id", "created")
    raw_id_fields = get_forward_relation_fields_for_model(model)
    show_change_link = True


@admin.register(models.Account)
class AccountAdmin(StripeModelAdmin):
    list_display = ("business_url", "country", "default_currency")
    list_filter = ("details_submitted",)
    search_fields = ("settings", "business_profile")


@admin.register(models.APIKey)
class APIKeyAdmin(StripeModelAdmin):
    list_display = ("type",)
    list_filter = ("type",)
    search_fields = ("name",)


@admin.register(models.BalanceTransaction)
class BalanceTransactionAdmin(ReadOnlyMixin, StripeModelAdmin):
    list_display = (
        "type",
        "net",
        "amount",
        "fee",
        "currency",
        "available_on",
        "status",
    )
    list_filter = ("status", "type")


@admin.register(models.Charge)
class ChargeAdmin(StripeModelAdmin):
    list_display = (
        "customer",
        "amount",
        "description",
        "paid",
        "disputed",
        "refunded",
        "fee",
    )
    list_select_related = (
        "customer",
        "customer__subscriber",
        "balance_transaction",
    )
    search_fields = ("customer__id", "invoice__id")
    list_filter = ("status", "paid", "refunded", "captured")


@admin.register(models.Coupon)
class CouponAdmin(StripeModelAdmin):
    list_display = (
        "amount_off",
        "percent_off",
        "duration",
        "duration_in_months",
        "redeem_by",
        "max_redemptions",
        "times_redeemed",
    )
    list_filter = ("duration", "redeem_by")
    radio_fields = {"duration": admin.HORIZONTAL}


@admin.register(models.Customer)
class CustomerAdmin(StripeModelAdmin):
    list_display = (
        "subscriber",
        "email",
        "currency",
        "default_source",
        "coupon",
        "balance",
        "business_vat_id",
    )
    list_select_related = ("subscriber", "default_source", "coupon")
    list_filter = (CustomerHasSourceListFilter, CustomerSubscriptionStatusListFilter)
    search_fields = ("email", "description")
    inlines = (SubscriptionInline,)


@admin.register(models.Dispute)
class DisputeAdmin(ReadOnlyMixin, StripeModelAdmin):
    list_display = ("reason", "status", "amount", "currency", "is_charge_refundable")
    list_filter = ("is_charge_refundable", "reason", "status")


@admin.register(models.Event)
class EventAdmin(ReadOnlyMixin, StripeModelAdmin):
    list_display = ("type", "request_id")
    list_filter = ("type", "created")
    search_fields = ("request_id",)


@admin.register(models.FileUpload)
class FileUploadAdmin(StripeModelAdmin):
    list_display = ("purpose", "size", "type")
    list_filter = ("purpose", "type")
    search_fields = ("filename",)


@admin.register(models.PaymentIntent)
class PaymentIntentAdmin(StripeModelAdmin):
    list_display = (
        "customer",
        "amount",
        "currency",
        "description",
        "amount_capturable",
        "amount_received",
        "receipt_email",
    )
    list_select_related = ("customer", "customer__subscriber")
    search_fields = ("customer__id", "invoice__id")


@admin.register(models.SetupIntent)
class SetupIntentAdmin(StripeModelAdmin):
    list_display = (
        "created",
        "customer",
        "description",
        "on_behalf_of",
        "payment_method",
        "payment_method_types",
        "status",
    )
    list_filter = ("status",)
    list_select_related = (
        "customer",
        "customer__subscriber",
        "payment_method",
    )
    search_fields = ("customer__id", "status")


@admin.register(models.Invoice)
class InvoiceAdmin(StripeModelAdmin):
    list_display = ("total", "paid", "currency", "number", "customer", "due_date")
    list_filter = (
        "paid",
        "attempted",
        "created",
        "due_date",
        "period_start",
        "period_end",
    )
    list_select_related = ("customer", "customer__subscriber")
    search_fields = ("customer__id", "number", "receipt_number")
    inlines = (InvoiceItemInline,)


@admin.register(models.Plan)
class PlanAdmin(StripeModelAdmin):
    radio_fields = {"interval": admin.HORIZONTAL}

    def get_readonly_fields(self, request, obj=None):
        """Return extra readonly_fields."""
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            readonly_fields += (
                "amount",
                "currency",
                "interval",
                "interval_count",
                "trial_period_days",
            )

        return readonly_fields


@admin.register(models.Price)
class PriceAdmin(StripeModelAdmin):
    list_display = ("product", "currency", "active")
    list_filter = ("active", "type", "billing_scheme", "tiers_mode")
    raw_id_fields = ("product",)
    search_fields = ("nickname",)
    radio_fields = {"type": admin.HORIZONTAL}


@admin.register(models.Product)
class ProductAdmin(StripeModelAdmin):
    list_display = ("name", "type", "active", "url", "statement_descriptor")
    list_filter = ("type", "active", "shippable")
    search_fields = ("name", "statement_descriptor")


@admin.register(models.Refund)
class RefundAdmin(StripeModelAdmin):
    list_display = (
        "amount",
        "currency",
        "charge",
        "reason",
        "status",
        "failure_reason",
    )
    list_filter = ("reason", "status")
    search_fields = ("receipt_number",)


@admin.register(models.Source)
class SourceAdmin(StripeModelAdmin):
    list_display = ("customer", "type", "status", "amount", "currency", "usage", "flow")
    list_filter = ("type", "status", "usage", "flow")
    list_select_related = ("customer", "customer__subscriber")


@admin.register(models.PaymentMethod)
class PaymentMethodAdmin(StripeModelAdmin):
    list_display = ("customer", "billing_details")
    list_filter = ("type",)
    list_select_related = ("customer", "customer__subscriber")
    search_fields = ("customer__id",)


@admin.register(models.Subscription)
class SubscriptionAdmin(StripeModelAdmin):
    list_display = ("customer", "status")
    list_filter = ("status", "cancel_at_period_end")
    list_select_related = ("customer", "customer__subscriber")

    inlines = (SubscriptionItemInline,)

    def _cancel(self, request, queryset):
        """Cancel a subscription."""
        for subscription in queryset:
            subscription.cancel()

    _cancel.short_description = "Cancel selected subscriptions"  # type: ignore # noqa

    actions = (_cancel,)


@admin.register(models.TaxRate)
class TaxRateAdmin(StripeModelAdmin):
    list_display = ("active", "display_name", "inclusive", "jurisdiction", "percentage")
    list_filter = ("active", "inclusive", "jurisdiction")


@admin.register(models.Transfer)
class TransferAdmin(StripeModelAdmin):
    list_display = ("amount", "description")
