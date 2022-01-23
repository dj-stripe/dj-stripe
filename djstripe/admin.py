"""
Django Administration interface definitions
"""
import json
from typing import Optional
from urllib.parse import urljoin

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.utils import display_for_field, display_for_value
from django.urls import reverse
from jsonfield import JSONField
from stripe.error import AuthenticationError, InvalidRequestError

from . import enums, models


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


class SubscriptionInline(admin.StackedInline):
    """A TabularInline for use models.Subscription."""

    model = models.Subscription
    extra = 0
    readonly_fields = ("id", "created", "djstripe_owner_account")
    raw_id_fields = get_forward_relation_fields_for_model(model)
    show_change_link = True


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


class APIKeyAdminCreateForm(forms.ModelForm):
    class Meta:
        model = models.APIKey
        fields = ["name", "secret"]

    def _post_clean(self):
        super()._post_clean()

        if not self.errors:
            if (
                self.instance.type == enums.APIKeyType.secret
                and self.instance.djstripe_owner_account is None
            ):
                try:
                    self.instance.refresh_account()
                except AuthenticationError as e:
                    self.add_error("secret", str(e))


@admin.register(models.APIKey)
class APIKeyAdmin(admin.ModelAdmin):
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
        "deleted",
        "subscriber",
        "email",
        "currency",
        "default_source",
        "coupon",
        "balance",
    )
    list_select_related = ("subscriber", "default_source", "coupon")
    list_filter = (
        CustomerHasSourceListFilter,
        CustomerSubscriptionStatusListFilter,
        "deleted",
    )
    search_fields = ("email", "description", "deleted")
    inlines = (SubscriptionInline, TaxIdInline)


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
    list_select_related = ("balance_transaction", "destination")
    list_filter = ("destination__id",)
    search_fields = ("destination__id", "balance_transaction__id")


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


@admin.register(models.Session)
class SessionAdmin(StripeModelAdmin):
    list_display = ("customer", "customer_email")
    list_filter = ("customer", "mode")
    search_fields = ("customer__id", "customer_email")


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


@admin.register(models.Mandate)
class MandateAdmin(StripeModelAdmin):
    list_display = ("status", "type", "payment_method")
    list_filter = ("multi_use", "single_use")
    list_select_related = ("payment_method",)
    search_fields = ("payment_method__id",)


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


@admin.register(models.Card)
class CardAdmin(StripeModelAdmin):
    list_display = ("customer", "account")
    list_select_related = ("customer", "customer__subscriber", "account")
    search_fields = ("customer__id", "account__id")


@admin.register(models.BankAccount)
class BankAccountAdmin(StripeModelAdmin):
    list_display = ("customer", "account")
    list_select_related = ("customer", "customer__subscriber", "account")
    search_fields = ("customer__id", "account__id")


@admin.register(models.Subscription)
class SubscriptionAdmin(StripeModelAdmin):
    list_display = ("customer", "status")
    list_filter = ("status", "cancel_at_period_end")
    list_select_related = ("customer", "customer__subscriber")

    inlines = (SubscriptionItemInline,)

    def _cancel(self, request, queryset):
        """Cancel a subscription."""
        for subscription in queryset:
            try:
                instance = subscription.cancel()
                self.message_user(
                    request,
                    f"Successfully Canceled: {instance}",
                    level=messages.SUCCESS,
                )
            except InvalidRequestError as error:
                self.message_user(request, str(error), level=messages.WARNING)

    _cancel.short_description = "Cancel selected subscriptions"  # type: ignore # noqa

    actions = (_cancel,)


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


@admin.register(models.UsageRecordSummary)
class UsageRecordSummaryAdmin(StripeModelAdmin):
    list_display = ("invoice", "subscription_item", "total_usage")


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
class WebhookEndpointAdmin(admin.ModelAdmin):
    change_form_template = "djstripe/admin/change_form.html"
    delete_confirmation_template = (
        "djstripe/admin/webhook_endpoint/delete_confirmation.html"
    )
    readonly_fields = ("url",)
    list_display = (
        "__str__",
        "djstripe_owner_account",
        "livemode",
        "created",
        "api_version",
    )

    # Disable the mass-delete action for webhook endpoints.
    # We don't want to enable deleting multiple endpoints on Stripe at once.
    def get_actions(self, request):
        return {}

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

    def get_changeform_initial_data(self, request) -> dict[str, str]:
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
