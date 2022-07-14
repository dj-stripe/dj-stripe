"""
Django Administration interface definitions
"""
from typing import Any, Dict

from django.contrib import admin
from django.db import IntegrityError, transaction
from django.shortcuts import render
from stripe.error import InvalidRequestError

from djstripe import models

from .actions import CustomActionMixin
from .admin_inline import (
    InvoiceItemInline,
    SubscriptionInline,
    SubscriptionItemInline,
    SubscriptionScheduleInline,
    TaxIdInline,
)
from .filters import CustomerHasSourceListFilter, CustomerSubscriptionStatusListFilter
from .forms import (
    APIKeyAdminCreateForm,
    CustomActionForm,
    WebhookEndpointAdminCreateForm,
    WebhookEndpointAdminEditForm,
)
from .utils import (
    ReadOnlyMixin,
    custom_display_for_JSONfield,
    get_forward_relation_fields_for_model,
)


def admin_display_for_field_override():
    admin.utils.display_for_field = custom_display_for_JSONfield
    admin.helpers.display_for_field = custom_display_for_JSONfield


# execute override
admin_display_for_field_override()


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


@admin.register(models.Order)
class OrderAdmin(StripeModelAdmin):
    list_display = (
        "amount_total",
        "customer",
        "status",
    )
    list_filter = (
        "customer",
        "status",
    )
    list_select_related = ("customer", "payment_intent")


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
        "status",
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

    def get_actions(self, request):
        """
        Returns _resync_instances only for
        models with a defined model.stripe_class.retrieve
        """
        actions = super().get_actions(request)

        # remove "_sync_all_instances" as Mandates cannot be listed
        actions.pop("_sync_all_instances", None)

        return actions


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


@admin.register(models.ShippingRate)
class ShippingRateAdmin(StripeModelAdmin):
    list_display = ("display_name", "active", "tax_behavior", "tax_code")
    list_filter = ("active", "tax_behavior")
    list_select_related = ("tax_code",)


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


@admin.register(models.TaxCode)
class TaxCodeAdmin(StripeModelAdmin):
    list_display = ("name", "description")
    list_filter = ("name",)


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

    def get_actions(self, request):
        """
        Returns _resync_instances only for
        models with a defined model.stripe_class.retrieve
        """
        actions = super().get_actions(request)

        # remove "_sync_all_instances" as UsageRecords cannot be listed
        actions.pop("_sync_all_instances", None)

        return actions


@admin.register(models.UsageRecordSummary)
class UsageRecordSummaryAdmin(StripeModelAdmin):
    list_display = ("invoice", "subscription_item", "total_usage")

    def get_queryset(self, request):
        return (
            super().get_queryset(request).select_related("invoice", "subscription_item")
        )


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
            advanced_fields = ["metadata", "api_version", "enabled_events"]

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
