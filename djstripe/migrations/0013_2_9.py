# Generated by Django 5.0.4 on 2024-04-25 12:22

import uuid

from django.db import migrations, models
from django.conf import settings

import djstripe.enums
import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ("djstripe", "0012_2_8"),
    ]

    operations = [
        migrations.RenameField(
            model_name="webhookendpoint",
            old_name="tolerance",
            new_name="djstripe_tolerance",
        ),
        migrations.AlterUniqueTogether(
            name="customer",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="account",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="apikey",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="applicationfee",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="applicationfeerefund",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="balancetransaction",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="bankaccount",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="card",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="charge",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="countryspec",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="coupon",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="customer",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="discount",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="dispute",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="event",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="file",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="filelink",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="invoice",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="invoiceitem",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="lineitem",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="mandate",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="paymentintent",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="paymentmethod",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="payout",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="plan",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="price",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="product",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="refund",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="scheduledqueryrun",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="session",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="setupintent",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="shippingrate",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="source",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="sourcetransaction",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="subscription",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="subscriptionitem",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="subscriptionschedule",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="taxcode",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="taxid",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="taxrate",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="transfer",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="transferreversal",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="upcominginvoice",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="usagerecord",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="usagerecordsummary",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="verificationreport",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="verificationsession",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="webhookendpoint",
            name="djstripe_validation_method",
            field=djstripe.fields.StripeEnumField(
                default="verify_signature",
                enum=djstripe.enums.WebhookEndpointValidation,
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="webhookendpoint",
            name="stripe_data",
            field=djstripe.fields.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="account",
            name="business_type",
            field=djstripe.fields.StripeEnumField(
                blank=True, default="", enum=djstripe.enums.BusinessType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="account",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.AccountType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="apikey",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.APIKeyType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="balancetransaction",
            name="reporting_category",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.BalanceTransactionReportingCategory, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="balancetransaction",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.BalanceTransactionStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="balancetransaction",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.BalanceTransactionType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="bankaccount",
            name="account_holder_type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.BankAccountHolderType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="bankaccount",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.BankAccountStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="card",
            name="address_line1_check",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.CardCheckResult,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="card",
            name="address_zip_check",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.CardCheckResult,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="card",
            name="brand",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.CardBrand, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="card",
            name="cvc_check",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.CardCheckResult,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="card",
            name="funding",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.CardFundingType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="card",
            name="tokenization_method",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.CardTokenizationMethod,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="charge",
            name="failure_code",
            field=djstripe.fields.StripeEnumField(
                blank=True, default="", enum=djstripe.enums.ApiErrorCode, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="charge",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.ChargeStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="coupon",
            name="duration",
            field=djstripe.fields.StripeEnumField(
                default="once", enum=djstripe.enums.CouponDuration, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="customer",
            name="tax_exempt",
            field=djstripe.fields.StripeEnumField(
                default="", enum=djstripe.enums.CustomerTaxExempt, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="dispute",
            name="reason",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.DisputeReason, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="dispute",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.DisputeStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="file",
            name="purpose",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.FilePurpose, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="file",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.FileType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="billing_reason",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.InvoiceBillingReason,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="collection_method",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.InvoiceCollectionMethod, max_length=255, null=True
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="customer_tax_exempt",
            field=djstripe.fields.StripeEnumField(
                default="", enum=djstripe.enums.CustomerTaxExempt, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="status",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.InvoiceStatus,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="invoiceorlineitem",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.InvoiceorLineItemType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="lineitem",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.LineItem, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="mandate",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.MandateStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="mandate",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.MandateType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="paymentintent",
            name="cancellation_reason",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                enum=djstripe.enums.PaymentIntentCancellationReason,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="paymentintent",
            name="capture_method",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.CaptureMethod, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="paymentintent",
            name="confirmation_method",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.ConfirmationMethod, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="paymentintent",
            name="setup_future_usage",
            field=djstripe.fields.StripeEnumField(
                blank=True, enum=djstripe.enums.IntentUsage, max_length=255, null=True
            ),
        ),
        migrations.AlterField(
            model_name="paymentintent",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.PaymentIntentStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="paymentmethod",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.PaymentMethodType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="payout",
            name="failure_code",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.PayoutFailureCode,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="payout",
            name="source_type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.PayoutSourceType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="payout",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.PayoutStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="payout",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.PayoutType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="plan",
            name="aggregate_usage",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.PlanAggregateUsage,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="plan",
            name="billing_scheme",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.BillingScheme,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="plan",
            name="interval",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.PlanInterval, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="plan",
            name="tiers_mode",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                enum=djstripe.enums.PriceTiersMode,
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="plan",
            name="usage_type",
            field=djstripe.fields.StripeEnumField(
                default="licensed", enum=djstripe.enums.PriceUsageType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="price",
            name="billing_scheme",
            field=djstripe.fields.StripeEnumField(
                blank=True, enum=djstripe.enums.BillingScheme, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="price",
            name="tiers_mode",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                enum=djstripe.enums.PriceTiersMode,
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="price",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.PriceType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.ProductType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="refund",
            name="failure_reason",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.RefundFailureReason,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="refund",
            name="reason",
            field=djstripe.fields.StripeEnumField(
                blank=True, default="", enum=djstripe.enums.RefundReason, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="refund",
            name="status",
            field=djstripe.fields.StripeEnumField(
                blank=True, enum=djstripe.enums.RefundStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="scheduledqueryrun",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.ScheduledQueryRunStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="session",
            name="billing_address_collection",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                enum=djstripe.enums.SessionBillingAddressCollection,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="session",
            name="mode",
            field=djstripe.fields.StripeEnumField(
                blank=True, enum=djstripe.enums.SessionMode, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="session",
            name="payment_status",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                enum=djstripe.enums.SessionPaymentStatus,
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="session",
            name="status",
            field=djstripe.fields.StripeEnumField(
                blank=True, enum=djstripe.enums.SessionStatus, max_length=255, null=True
            ),
        ),
        migrations.AlterField(
            model_name="session",
            name="submit_type",
            field=djstripe.fields.StripeEnumField(
                blank=True, enum=djstripe.enums.SubmitTypeStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="setupintent",
            name="cancellation_reason",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                enum=djstripe.enums.SetupIntentCancellationReason,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="setupintent",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.SetupIntentStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="setupintent",
            name="usage",
            field=djstripe.fields.StripeEnumField(
                default="off_session", enum=djstripe.enums.IntentUsage, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="shippingrate",
            name="tax_behavior",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.ShippingRateTaxBehavior, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="shippingrate",
            name="type",
            field=djstripe.fields.StripeEnumField(
                default="fixed_amount",
                enum=djstripe.enums.ShippingRateType,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="source",
            name="flow",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.SourceFlow, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="source",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.SourceStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="source",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.SourceType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="source",
            name="usage",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.SourceUsage, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="sourcetransaction",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.SourceTransactionStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="collection_method",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.InvoiceCollectionMethod, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="proration_behavior",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="create_prorations",
                enum=djstripe.enums.SubscriptionProrationBehavior,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.SubscriptionStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="subscriptionitem",
            name="proration_behavior",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="create_prorations",
                enum=djstripe.enums.SubscriptionProrationBehavior,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="subscriptionschedule",
            name="end_behavior",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.SubscriptionScheduleEndBehavior, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="subscriptionschedule",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.SubscriptionScheduleStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="taxid",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.TaxIdType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="transfer",
            name="source_type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.LegacySourceType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="upcominginvoice",
            name="billing_reason",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.InvoiceBillingReason,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="upcominginvoice",
            name="collection_method",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.InvoiceCollectionMethod, max_length=255, null=True
            ),
        ),
        migrations.AlterField(
            model_name="upcominginvoice",
            name="customer_tax_exempt",
            field=djstripe.fields.StripeEnumField(
                default="", enum=djstripe.enums.CustomerTaxExempt, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="upcominginvoice",
            name="status",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.InvoiceStatus,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="usagerecord",
            name="action",
            field=djstripe.fields.StripeEnumField(
                default="increment", enum=djstripe.enums.UsageAction, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="verificationreport",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.VerificationType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="verificationsession",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.VerificationSessionStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="verificationsession",
            name="type",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.VerificationType, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="webhookendpoint",
            name="djstripe_uuid",
            field=models.UUIDField(
                default=uuid.uuid4,
                help_text="A UUID specific to dj-stripe generated for the endpoint",
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="webhookendpoint",
            name="status",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.WebhookEndpointStatus, max_length=255
            ),
        ),
        migrations.AlterField(
            model_name="webhookendpoint",
            name="api_version",
            field=models.CharField(
                blank=True,
                default="2024-04-10",
                help_text="The API version events are rendered as for this webhook endpoint. Defaults to the configured Stripe API Version.",
                max_length=64,
            ),
        ),
        migrations.DeleteModel(
            name="Order",
        ),
        migrations.CreateModel(
            name="PromotionCode",
            fields=[
                ("djstripe_created", models.DateTimeField(auto_now_add=True)),
                ("djstripe_updated", models.DateTimeField(auto_now=True)),
                ("stripe_data", djstripe.fields.JSONField(default=dict)),
                (
                    "djstripe_id",
                    models.BigAutoField(
                        primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("id", djstripe.fields.StripeIdField(max_length=255, unique=True)),
                (
                    "livemode",
                    models.BooleanField(
                        blank=True,
                        default=None,
                        help_text="Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.",
                        null=True,
                    ),
                ),
                ("created", djstripe.fields.StripeDateTimeField(blank=True, null=True)),
                ("metadata", djstripe.fields.JSONField(blank=True, null=True)),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="A description of this object.", null=True
                    ),
                ),
                (
                    "djstripe_owner_account",
                    djstripe.fields.StripeForeignKey(
                        blank=True,
                        help_text="The Stripe Account this object belongs to.",
                        null=True,
                        on_delete=models.deletion.CASCADE,
                        to="djstripe.account",
                        to_field=settings.DJSTRIPE_FOREIGN_KEY_TO_FIELD,
                    ),
                ),
            ],
            options={
                "get_latest_by": "created",
                "abstract": False,
            },
        ),
    ]
