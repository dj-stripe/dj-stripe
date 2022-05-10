"""
Django Administration interface definitions
"""
import json
from typing import Any, Dict, Optional
from urllib.parse import urljoin

from django import forms
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.utils import display_for_field, display_for_value, quote
from django.db import IntegrityError, transaction
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import capfirst
from jsonfield import JSONField
from stripe.error import InvalidRequestError

from djstripe.forms import APIKeyAdminCreateForm, CustomActionForm

from . import models


def custom_display_for_JSONfield(value, field, empty_value_display):
    """
    Overriding display_for_field to correctly render JSONField READonly fields
    in django-admin. Relevant when DJSTRIPE_USE_NATIVE_JSONFIELD is False
    Note: This does not handle invalid JSON. That should be handled by the JSONField itself
    """
    # we manually JSON serialise in case field is from jsonfield module
    if isinstance(field, JSONField) and value:
        try:
            return json.dumps(value)
        except TypeError:
            return display_for_value(value, empty_value_display)
    return display_for_field(value, field, empty_value_display)


def admin_display_for_field_override():
    admin.utils.display_for_field = custom_display_for_JSONfield
    admin.helpers.display_for_field = custom_display_for_JSONfield


# execute override
admin_display_for_field_override()


class CustomActionMixin:

    # So that actions get shown even if there are 0 instances
    # https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.show_full_result_count
    show_full_result_count = False

    def get_admin_action_context(self, queryset, action_name, form_class):

        context = {
            "action_name": action_name,
            "model_name": self.model._meta.model_name,
            "info": [],
            "queryset": queryset,
            "changelist_url": reverse(
                f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist"
            ),
            "ACTION_CHECKBOX_NAME": helpers.ACTION_CHECKBOX_NAME,
            "form": form_class(
                initial={
                    helpers.ACTION_CHECKBOX_NAME: queryset.values_list("pk", flat=True)
                },
                model_name=self.model._meta.model_name,
                action_name=action_name,
            ),
        }

        if action_name == "_sync_all_instances":
            context["form"] = form_class(
                initial={helpers.ACTION_CHECKBOX_NAME: [action_name]},
                model_name=self.model._meta.model_name,
                action_name=action_name,
            )

        else:
            for obj in queryset:
                admin_url = reverse(
                    f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
                    None,
                    (quote(obj.pk),),
                )
                context["info"].append(
                    format_html(
                        '{}: <a href="{}">{}</a>',
                        capfirst(obj._meta.verbose_name),
                        admin_url,
                        obj,
                    )
                )
        return context

    def get_actions(self, request):
        """
        Returns _resync_instances only for
        models with a defined model.stripe_class.retrieve
        """
        actions = super().get_actions(request)

        # ensure we return "_resync_instances" ONLY for
        # models that have a GET method
        if not getattr(self.model.stripe_class, "retrieve", None):
            actions.pop("_resync_instances", None)

        return actions

    @admin.action(description="Re-Sync Selected Instances")
    def _resync_instances(self, request, queryset):
        """Admin Action to resync selected instances"""
        context = self.get_admin_action_context(
            queryset, "_resync_instances", CustomActionForm
        )
        return render(request, "djstripe/admin/confirm_action.html", context)

    @admin.action(description="Sync All Instances for all API Keys")
    def _sync_all_instances(self, request, queryset):
        """Admin Action to Sync All Instances"""
        context = self.get_admin_action_context(
            queryset, "_sync_all_instances", CustomActionForm
        )
        return render(request, "djstripe/admin/confirm_action.html", context)

    def changelist_view(self, request, extra_context=None):
        # we fool it into thinking we have selected some query
        # since we need to sync all instances
        post = request.POST.copy()
        if (
            helpers.ACTION_CHECKBOX_NAME not in post
            and post.get("action") == "_sync_all_instances"
        ):
            post[helpers.ACTION_CHECKBOX_NAME] = None
            request._set_post(post)
        return super().changelist_view(request, extra_context)


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
        "stripe_trigger_account",
        "webhook_endpoint",
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

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("stripe_trigger_account", "event", "webhook_endpoint")
        )


class StripeModelAdmin(CustomActionMixin, admin.ModelAdmin):
    """Base class for all StripeModel-based model admins"""

    change_form_template = "djstripe/admin/change_form.html"
    add_form_template = "djstripe/admin/add_form.html"
    actions = ("_resync_instances", "_sync_all_instances")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.raw_id_fields = get_forward_relation_fields_for_model(self.model)

    def get_list_display(self, request):
        return (
            ("__str__", "id", "djstripe_owner_account")
            + self.list_display
            + ("created", "livemode")
        )

    def get_list_filter(self, request):
        return self.list_filter + ("created", "livemode")

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + ("id", "djstripe_owner_account", "created")

    def get_search_fields(self, request):
        return self.search_fields + ("id",)

    def get_fieldsets(self, request, obj=None):
        common_fields = ("livemode", "id", "djstripe_owner_account", "created")
        # Have to remove the fields from the common set,
        # otherwise they'll show up twice.
        fields = [f for f in self.get_fields(request, obj) if f not in common_fields]
        return (
            (None, {"fields": common_fields}),
            (self.model.__name__, {"fields": fields}),
        )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("djstripe_owner_account")


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


@admin.register(models.Account)
class AccountAdmin(StripeModelAdmin):
    list_display = ("business_url", "country", "default_currency")
    list_filter = ("details_submitted",)
    search_fields = ("settings", "business_profile")


@admin.register(models.APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    add_form_template = "djstripe/admin/add_form.html"
    change_form_template = "djstripe/admin/change_form.html"

    list_display = ("__str__", "type", "djstripe_owner_account", "livemode")
    readonly_fields = ("djstripe_owner_account", "livemode", "type", "secret")
    search_fields = ("name",)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ["djstripe_owner_account", "livemode", "type"]
        return super().get_readonly_fields(request, obj=obj)

    def get_fields(self, request, obj=None):
        if obj is None:
            return APIKeyAdminCreateForm.Meta.fields
        return ["type", "djstripe_owner_account", "livemode", "name", "secret"]

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            return APIKeyAdminCreateForm
        return super().get_form(request, obj, **kwargs)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("djstripe_owner_account")

    def save_model(self, request: Any, obj, form: Any, change: Any) -> None:
        try:
            # for non-existent Platform Accounts, because of Account._find_owner_account()
            # it will try to retrieve by api_key, Account.get_or_retrieve_for_api_key().
            # Account.get_or_retrieve_for_api_key will create this APIKey! This would cause
            # an IntegrityError as the APIKey gets created before this form gets saved
            with transaction.atomic():
                obj.save()
        except IntegrityError:
            pass


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
        "invoice",
        "payment_method",
        "description",
        "paid",
        "disputed",
        "refunded",
        "fee",
    )

    search_fields = ("customer__id", "invoice__id")
    list_filter = ("status", "paid", "refunded", "captured")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "balance_transaction",
                "customer",
                "invoice",
                "payment_method",
                "payment_method__customer",
            )
        )


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
        "deleted",
        "subscriber",
        "email",
        "currency",
        "default_source",
        "default_payment_method",
        "coupon",
        "balance",
    )

    list_filter = (
        CustomerHasSourceListFilter,
        CustomerSubscriptionStatusListFilter,
        "deleted",
    )
    search_fields = ("email", "description", "deleted")
    inlines = (SubscriptionInline, SubscriptionScheduleInline, TaxIdInline)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "subscriber", "default_source", "default_payment_method", "coupon"
            )
        )


@admin.register(models.Dispute)
class DisputeAdmin(ReadOnlyMixin, StripeModelAdmin):
    list_display = ("reason", "status", "amount", "currency", "is_charge_refundable")
    list_filter = ("is_charge_refundable", "reason", "status")


@admin.register(models.Event)
class EventAdmin(ReadOnlyMixin, StripeModelAdmin):
    list_display = ("type", "request_id")
    list_filter = ("type", "created")
    search_fields = ("request_id",)


@admin.register(models.File)
class FileAdmin(StripeModelAdmin):
    list_display = ("purpose", "size", "type")
    list_filter = ("purpose", "type")
    search_fields = ("filename",)


@admin.register(models.FileLink)
class FileLinkAdmin(StripeModelAdmin):
    list_display = ("url",)
    list_filter = ("expires_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("file")


@admin.register(models.PaymentIntent)
class PaymentIntentAdmin(StripeModelAdmin):
    list_display = (
        "on_behalf_of",
        "customer",
        "amount",
        "payment_method",
        "currency",
        "description",
        "amount_capturable",
        "amount_received",
        "receipt_email",
    )
    search_fields = ("customer__id", "invoice__id")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "customer", "payment_method", "payment_method__customer", "on_behalf_of"
            )
        )


@admin.register(models.Payout)
class PayoutAdmin(StripeModelAdmin):
    list_display = (
        "destination",
        "amount",
        "arrival_date",
        "method",
        "status",
        "type",
    )
    list_filter = ("destination__id",)
    search_fields = ("destination__id", "balance_transaction__id")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("balance_transaction", "destination")
        )


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
    search_fields = ("customer__id", "status")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "on_behalf_of",
                "customer",
                "customer__subscriber",
                "payment_method",
                "payment_method__customer",
            )
        )


@admin.register(models.Session)
class SessionAdmin(StripeModelAdmin):
    list_display = ("customer", "customer_email", "subscription")
    list_filter = ("customer", "mode")
    search_fields = ("customer__id", "customer_email")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("customer", "subscription")


@admin.register(models.Invoice)
class InvoiceAdmin(StripeModelAdmin):
    list_display = (
        "total",
        "get_default_tax_rates",
        "paid",
        "currency",
        "number",
        "customer",
        "due_date",
    )
    list_filter = (
        "paid",
        "attempted",
        "created",
        "due_date",
        "period_start",
        "period_end",
    )
    search_fields = ("customer__id", "number", "receipt_number")
    inlines = (InvoiceItemInline,)

    @admin.display(description="Default Tax Rates")
    def get_default_tax_rates(self, obj):
        result = [str(tax_rate) for tax_rate in obj.default_tax_rates.all()]
        if result:
            return ", ".join(result)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("customer")
            .prefetch_related("default_tax_rates")
        )


@admin.register(models.Mandate)
class MandateAdmin(StripeModelAdmin):
    list_display = ("status", "type", "payment_method")
    list_filter = ("multi_use", "single_use")
    search_fields = ("payment_method__id",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("payment_method")


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

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("product")
            .prefetch_related("subscriptions")
        )


@admin.register(models.Price)
class PriceAdmin(StripeModelAdmin):
    list_display = ("product", "currency", "active")
    list_filter = ("active", "type", "billing_scheme", "tiers_mode")
    raw_id_fields = ("product",)
    search_fields = ("nickname",)
    radio_fields = {"type": admin.HORIZONTAL}

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("product")
            .prefetch_related("product__prices")
        )


@admin.register(models.Product)
class ProductAdmin(StripeModelAdmin):
    list_display = ("name", "type", "active", "url", "statement_descriptor")
    list_filter = ("type", "active", "shippable")
    search_fields = ("name", "statement_descriptor")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("prices")


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

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("charge")


@admin.register(models.Source)
class SourceAdmin(StripeModelAdmin):
    list_display = ("customer", "type", "status", "amount", "currency", "usage", "flow")
    list_filter = ("type", "status", "usage", "flow")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("customer", "customer__subscriber")
        )


@admin.register(models.PaymentMethod)
class PaymentMethodAdmin(StripeModelAdmin):
    list_display = ("customer", "type", "billing_details")
    list_filter = ("type",)
    search_fields = ("customer__id",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("customer", "customer__subscriber")
        )


@admin.register(models.Card)
class CardAdmin(StripeModelAdmin):
    list_display = ("customer", "account")
    search_fields = ("customer__id", "account__id")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "customer",
                "customer__default_source",
                "customer__default_payment_method",
                "account",
            )
        )


@admin.register(models.BankAccount)
class BankAccountAdmin(StripeModelAdmin):
    list_display = ("customer", "account")
    search_fields = ("customer__id", "account__id")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "customer",
                "customer__default_source",
                "customer__default_payment_method",
                "account",
            )
        )


@admin.register(models.Subscription)
class SubscriptionAdmin(StripeModelAdmin):
    list_display = ("customer", "status", "get_default_tax_rates")
    list_filter = ("status", "cancel_at_period_end")

    inlines = (SubscriptionItemInline, SubscriptionScheduleInline)

    def get_actions(self, request):
        # get all actions
        actions = super().get_actions(request)
        actions["_cancel"] = self.get_action("_cancel")
        return actions

    @admin.action(description="Cancel selected subscriptions")
    def _cancel(self, request, queryset):
        """Cancel a subscription."""
        context = self.get_admin_action_context(queryset, "_cancel", CustomActionForm)
        return render(request, "djstripe/admin/confirm_action.html", context)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "customer",
            )
            .prefetch_related(
                "customer__subscriptions",
                "customer__subscriptions__plan",
                "customer__subscriptions__plan__product",
                "default_tax_rates",
            )
        )

    @admin.display(description="Default Tax Rates")
    def get_default_tax_rates(self, obj):
        result = [str(tax_rate) for tax_rate in obj.default_tax_rates.all()]
        if result:
            return ", ".join(result)


@admin.register(models.SubscriptionSchedule)
class SubscriptionScheduleAdmin(StripeModelAdmin):
    list_display = ("status", "subscription", "current_phase", "customer")
    list_filter = ("status", "subscription", "customer")
    list_select_related = ("customer", "customer__subscriber", "subscription")

    @admin.display(description="Release Selected Subscription Schedules")
    def _release_subscription_schedule(self, request, queryset):
        """Release a SubscriptionSchedule."""
        context = self.get_admin_action_context(
            queryset, "_release_subscription_schedule", CustomActionForm
        )
        return render(request, "djstripe/admin/confirm_action.html", context)

    @admin.display(description="Cancel Selected Subscription Schedules")
    def _cancel_subscription_schedule(self, request, queryset):
        """Cancel a SubscriptionSchedule."""
        context = self.get_admin_action_context(
            queryset, "_cancel_subscription_schedule", CustomActionForm
        )
        return render(request, "djstripe/admin/confirm_action.html", context)

    def get_actions(self, request):
        # get all actions
        actions = super().get_actions(request)
        actions["_release_subscription_schedule"] = self.get_action(
            "_release_subscription_schedule"
        )
        actions["_cancel_subscription_schedule"] = self.get_action(
            "_cancel_subscription_schedule"
        )
        return actions


@admin.register(models.TaxRate)
class TaxRateAdmin(StripeModelAdmin):
    list_display = ("active", "display_name", "inclusive", "jurisdiction", "percentage")
    list_filter = ("active", "inclusive", "jurisdiction")


@admin.register(models.Transfer)
class TransferAdmin(StripeModelAdmin):
    list_display = ("amount", "description")


@admin.register(models.TransferReversal)
class TransferReversalAdmin(StripeModelAdmin):
    list_display = ("amount", "transfer")


@admin.register(models.ApplicationFee)
class ApplicationFeeAdmin(StripeModelAdmin):
    list_display = ("amount", "account")


@admin.register(models.ApplicationFeeRefund)
class ApplicationFeeReversalAdmin(StripeModelAdmin):
    list_display = ("amount", "fee")


@admin.register(models.UsageRecord)
class UsageRecordAdmin(StripeModelAdmin):
    list_display = ("quantity", "subscription_item", "timestamp")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("subscription_item")


@admin.register(models.UsageRecordSummary)
class UsageRecordSummaryAdmin(StripeModelAdmin):
    list_display = ("invoice", "subscription_item", "total_usage")

    def get_queryset(self, request):
        return (
            super().get_queryset(request).select_related("invoice", "subscription_item")
        )


class WebhookEndpointAdminBaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].help_text = ""
        self.fields["description"].widget.attrs["rows"] = 3

    def _get_field_name(self, stripe_field: Optional[str]) -> Optional[str]:
        if stripe_field is None:
            return None
        if stripe_field == "url":
            return "base_url"
        else:
            return stripe_field.partition("[")[0]

    def save(self, commit: bool = False):
        # If we do the following in _post_clean(), the data doesn't save properly.
        assert self._stripe_data

        # Update scenario
        # Add back secret if endpoint already exists
        if self.instance.pk and not self._stripe_data.get("secret"):
            self._stripe_data["secret"] = self.instance.secret

        # Retrieve the api key that was used to create the endpoint
        api_key = getattr(self, "_stripe_api_key", None)
        if api_key:
            self.instance = models.WebhookEndpoint.sync_from_stripe_data(
                self._stripe_data, api_key=api_key
            )
        else:
            self.instance = models.WebhookEndpoint.sync_from_stripe_data(
                self._stripe_data
            )
        return super().save(commit=commit)


class WebhookEndpointAdminCreateForm(WebhookEndpointAdminBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["djstripe_owner_account"].label = "Stripe account"
        self.fields["djstripe_owner_account"].help_text = ""

    livemode = forms.BooleanField(
        label="Live mode",
        required=False,
        help_text="Whether to create this endpoint in live mode or test mode",
    )
    base_url = forms.URLField(
        required=True,
        help_text=(
            "Sets the base URL (scheme and host) for the endpoint. "
            "The final full URL will be auto-generated by dj-stripe."
        ),
    )
    connect = forms.BooleanField(
        label="Listen to events on Connected accounts",
        initial=False,
        required=False,
        help_text=(
            "Clients can make requests as connected accounts using the special "
            "header `Stripe-Account` which should contain a Stripe account ID "
            "(usually starting with the prefix `acct_`)."
        ),
    )

    class Meta:
        model = models.WebhookEndpoint
        fields = (
            "livemode",
            "djstripe_owner_account",
            "description",
            "base_url",
            "connect",
            "api_version",
            "metadata",
        )

    # Hook into _post_clean() instead of save().
    # This is used by Django for ModelForm logic. It's internal, but exactly
    # what we need to add errors after the data has been validated locally.
    def _post_clean(self):
        base_url = self.cleaned_data["base_url"]
        url_path = reverse(
            "djstripe:djstripe_webhook_by_uuid",
            kwargs={"uuid": self.instance.djstripe_uuid},
        )
        url = urljoin(base_url, url_path, allow_fragments=False)

        metadata = self.instance.metadata or {}
        metadata["djstripe_uuid"] = str(self.instance.djstripe_uuid)

        _api_key = {}
        account = self.cleaned_data["djstripe_owner_account"]
        livemode = self.cleaned_data["livemode"]
        if account:
            self._stripe_api_key = _api_key["api_key"] = account.get_default_api_key(
                livemode=livemode
            )

        try:
            self._stripe_data = models.WebhookEndpoint._api_create(
                url=url,
                api_version=self.cleaned_data["api_version"] or None,
                description=self.cleaned_data["description"],
                enabled_events=["*"],
                metadata=metadata,
                connect=self.cleaned_data["connect"],
                **_api_key,
            )
        except InvalidRequestError as e:
            field_name = self._get_field_name(e.param)
            self.add_error(field_name, e.user_message)

        return super()._post_clean()


class WebhookEndpointAdminEditForm(WebhookEndpointAdminBaseForm):
    base_url = forms.URLField(
        required=False,
        help_text=(
            "Updating this changes the base URL of the endpoint. "
            "MUST be publicly-accessible."
        ),
    )
    enabled = forms.BooleanField(
        initial=True,
        required=False,
        help_text="When disabled, the endpoint will not receive events.",
    )

    class Meta:
        model = models.WebhookEndpoint
        fields = ("description", "base_url", "enabled_events", "metadata")

    def get_initial_for_field(self, field, field_name):
        if field_name == "base_url":
            metadata = self.instance.metadata or {}
            djstripe_uuid = metadata.get("djstripe_uuid")
            if djstripe_uuid:
                # if a djstripe_uuid is set (for dj-stripe endpoints), set the base_url
                endpoint_path = reverse(
                    "djstripe:djstripe_webhook_by_uuid", kwargs={"uuid": djstripe_uuid}
                )
                return self.instance.url.replace(endpoint_path, "")
        return super().get_initial_for_field(field, field_name)

    def _post_clean(self):
        base_url = self.cleaned_data.get("base_url", "")
        if base_url and self.instance.djstripe_uuid:
            url_path = reverse(
                "djstripe:djstripe_webhook_by_uuid",
                kwargs={"uuid": self.instance.djstripe_uuid},
            )
            url = urljoin(base_url, url_path, allow_fragments=False)
        else:
            url = self.instance.url

        try:
            self._stripe_data = self.instance._api_update(
                url=url,
                description=self.cleaned_data.get("description"),
                enabled_events=self.cleaned_data.get("enabled_events"),
                metadata=self.cleaned_data.get("metadata"),
                disabled=(not self.cleaned_data.get("enabled")),
            )
        except InvalidRequestError as e:
            field_name = self._get_field_name(e.param)
            self.add_error(field_name, e.user_message)

        return super()._post_clean()


@admin.register(models.WebhookEndpoint)
class WebhookEndpointAdmin(CustomActionMixin, admin.ModelAdmin):
    change_form_template = "djstripe/admin/webhook_endpoint/change_form.html"
    delete_confirmation_template = (
        "djstripe/admin/webhook_endpoint/delete_confirmation.html"
    )
    add_form_template = "djstripe/admin/webhook_endpoint/add_form.html"
    readonly_fields = ("url",)
    list_display = (
        "__str__",
        "djstripe_owner_account",
        "livemode",
        "created",
        "api_version",
    )
    actions = ("_resync_instances", "_sync_all_instances")

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Disable the mass-delete action for webhook endpoints.
        # We don't want to enable deleting multiple endpoints on Stripe at once.
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            return WebhookEndpointAdminEditForm
        return WebhookEndpointAdminCreateForm

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return (
                "id",
                "livemode",
                "api_version",
                "url",
                "created",
                "djstripe_owner_account",
                "djstripe_uuid",
            )
        return super().get_readonly_fields(request, obj=obj)

    def get_fieldsets(self, request, obj=None):
        if obj:
            # if djstripe_uuid is null, this is not a dj-stripe webhook
            header_fields = ["id", "livemode", "djstripe_owner_account", "url"]
            advanced_fields = [
                "enabled_events",
                "metadata",
                "api_version",
                "djstripe_uuid",
            ]
            if obj.djstripe_uuid:
                core_fields = ["enabled", "base_url", "description"]
            else:
                core_fields = ["enabled", "description"]
        else:
            header_fields = ["djstripe_owner_account", "livemode"]
            core_fields = ["description", "base_url", "connect"]
            advanced_fields = ["metadata", "api_version"]

        return [
            (None, {"fields": header_fields}),
            ("Endpoint configuration", {"fields": core_fields}),
            (
                "Advanced",
                {"fields": advanced_fields, "classes": ["collapse"]},
            ),
        ]

    def get_changeform_initial_data(self, request) -> Dict[str, str]:
        ret = super().get_changeform_initial_data(request)
        base_url = f"{request.scheme}://{request.get_host()}"
        ret.setdefault("base_url", base_url)
        return ret

    def delete_model(self, request, obj: models.WebhookEndpoint):
        try:
            obj._api_delete()
        except InvalidRequestError as e:
            if e.user_message.startswith("No such webhook endpoint: "):
                # Webhook was already deleted in Stripe
                pass
            else:
                raise

        return super().delete_model(request, obj)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("djstripe_owner_account")
