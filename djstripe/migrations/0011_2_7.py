# Generated by Django 3.2.11 on 2022-01-19 04:59

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import djstripe.enums
import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ("djstripe", "0010_alter_customer_balance"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="subscriptionschedule",
            name="billing_thresholds",
        ),
        migrations.AddField(
            model_name="webhookeventtrigger",
            name="webhook_endpoint",
            field=djstripe.fields.StripeForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="djstripe.webhookendpoint",
                to_field=settings.DJSTRIPE_FOREIGN_KEY_TO_FIELD,
            ),
        ),
        migrations.AddField(
            model_name="account",
            name="djstripe_owner_account",
            field=djstripe.fields.StripeForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="djstripe.account",
                to_field=settings.DJSTRIPE_FOREIGN_KEY_TO_FIELD,
            ),
        ),
        migrations.AlterField(
            model_name="event",
            name="api_version",
            field=models.CharField(
                blank=True,
                help_text="the API version at which the event data was rendered. Blank for old entries only, all new entries will have this value",
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="webhookendpoint",
            name="api_version",
            field=models.CharField(
                max_length=64,
                blank=True,
                help_text="The API version events are rendered as for this webhook endpoint. Defaults to the configured Stripe API Version.",
            ),
        ),
        migrations.AddField(
            model_name="coupon",
            name="applies_to",
            field=djstripe.fields.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="subscriptionschedule",
            name="subscription",
            field=models.ForeignKey(
                blank=True,
                help_text="ID of the subscription managed by the subscription schedule.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="subscriptions",
                to="djstripe.subscription",
            ),
        ),
        migrations.AddField(
            model_name="taxrate",
            name="country",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Two-letter country code.",
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name="taxrate",
            name="state",
            field=models.CharField(
                blank=True,
                default="",
                help_text="ISO 3166-2 subdivision code, without country prefix.",
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name="taxrate",
            name="tax_type",
            field=models.CharField(
                blank=True,
                default="",
                help_text="The high-level tax type, such as vat, gst, sales_tax or custom.",
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name="payout",
            name="failure_code",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.PayoutFailureCode,
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="billing_reason",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.InvoiceBillingReason,
                max_length=38,
            ),
        ),
        migrations.AlterField(
            model_name="upcominginvoice",
            name="billing_reason",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="",
                enum=djstripe.enums.InvoiceBillingReason,
                max_length=38,
            ),
        ),
        migrations.AddField(
            model_name="subscriptionitem",
            name="proration_behavior",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="create_prorations",
                enum=djstripe.enums.SubscriptionProrationBehavior,
                help_text="Determines how to handle prorations when the billing cycle changes (e.g., when switching plans, resetting billing_cycle_anchor=now, or starting a trial), or if an item’s quantity changes",
                max_length=17,
            ),
        ),
        migrations.AddField(
            model_name="subscriptionitem",
            name="proration_date",
            field=djstripe.fields.StripeDateTimeField(
                blank=True,
                help_text="If set, the proration will be calculated as though the subscription was updated at the given time. This can be used to apply exactly the same proration that was previewed with upcoming invoice endpoint. It can also be used to implement custom proration logic, such as prorating by day instead of by second, by providing the time that you wish to use for proration calculations",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="proration_behavior",
            field=djstripe.fields.StripeEnumField(
                blank=True,
                default="create_prorations",
                enum=djstripe.enums.SubscriptionProrationBehavior,
                help_text="Determines how to handle prorations when the billing cycle changes (e.g., when switching plans, resetting billing_cycle_anchor=now, or starting a trial), or if an item’s quantity changes",
                max_length=17,
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="proration_date",
            field=djstripe.fields.StripeDateTimeField(
                blank=True,
                help_text="If set, the proration will be calculated as though the subscription was updated at the given time. This can be used to apply exactly the same proration that was previewed with upcoming invoice endpoint. It can also be used to implement custom proration logic, such as prorating by day instead of by second, by providing the time that you wish to use for proration calculations",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="pause_collection",
            field=djstripe.fields.JSONField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="TaxCode",
            fields=[
                ("djstripe_created", models.DateTimeField(auto_now_add=True)),
                ("djstripe_updated", models.DateTimeField(auto_now=True)),
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
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="A description of this object.", null=True
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="A short name for the tax code.", max_length=128
                    ),
                ),
                (
                    "djstripe_owner_account",
                    djstripe.fields.StripeForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="djstripe.account",
                        to_field=settings.DJSTRIPE_FOREIGN_KEY_TO_FIELD,
                    ),
                ),
            ],
            options={
                "verbose_name": "Tax Code",
            },
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("djstripe_created", models.DateTimeField(auto_now_add=True)),
                ("djstripe_updated", models.DateTimeField(auto_now=True)),
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
                ("amount_subtotal", djstripe.fields.StripeQuantumCurrencyAmountField()),
                ("amount_total", djstripe.fields.StripeQuantumCurrencyAmountField()),
                (
                    "application",
                    models.CharField(
                        blank=True,
                        help_text="ID of the Connect application that created the Order, if any.",
                        max_length=255,
                    ),
                ),
                ("automatic_tax", djstripe.fields.JSONField()),
                ("billing_details", djstripe.fields.JSONField(blank=True, null=True)),
                (
                    "client_secret",
                    models.TextField(
                        help_text="The client secret of this PaymentIntent. Used for client-side retrieval using a publishable key.",
                        max_length=5000,
                    ),
                ),
                ("currency", djstripe.fields.StripeCurrencyCodeField(max_length=3)),
                ("discounts", djstripe.fields.JSONField(blank=True, null=True)),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True,
                        help_text="A recent IP address of the purchaser used for tax reporting and tax location inference.",
                        null=True,
                    ),
                ),
                ("line_items", djstripe.fields.JSONField()),
                ("payment", djstripe.fields.JSONField()),
                ("shipping_cost", djstripe.fields.JSONField(blank=True, null=True)),
                ("shipping_details", djstripe.fields.JSONField(blank=True, null=True)),
                (
                    "status",
                    djstripe.fields.StripeEnumField(
                        enum=djstripe.enums.OrderStatus, max_length=10
                    ),
                ),
                ("tax_details", djstripe.fields.JSONField(blank=True, null=True)),
                ("total_details", djstripe.fields.JSONField()),
                (
                    "customer",
                    djstripe.fields.StripeForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="djstripe.customer",
                        to_field=settings.DJSTRIPE_FOREIGN_KEY_TO_FIELD,
                    ),
                ),
                (
                    "djstripe_owner_account",
                    djstripe.fields.StripeForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="djstripe.account",
                        to_field=settings.DJSTRIPE_FOREIGN_KEY_TO_FIELD,
                    ),
                ),
                (
                    "payment_intent",
                    djstripe.fields.StripeForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="djstripe.paymentintent",
                        to_field=settings.DJSTRIPE_FOREIGN_KEY_TO_FIELD,
                    ),
                ),
            ],
            options={
                "get_latest_by": "created",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ShippingRate",
            fields=[
                ("djstripe_created", models.DateTimeField(auto_now_add=True)),
                ("djstripe_updated", models.DateTimeField(auto_now=True)),
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
                    "active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the shipping rate can be used for new purchases. Defaults to true",
                    ),
                ),
                (
                    "display_name",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="The name of the shipping rate, meant to be displayable to the customer. This will appear on CheckoutSessions.",
                        max_length=50,
                    ),
                ),
                ("fixed_amount", djstripe.fields.JSONField()),
                (
                    "type",
                    djstripe.fields.StripeEnumField(
                        default="fixed_amount",
                        enum=djstripe.enums.ShippingRateType,
                        max_length=12,
                    ),
                ),
                ("delivery_estimate", djstripe.fields.JSONField(blank=True, null=True)),
                (
                    "tax_behavior",
                    djstripe.fields.StripeEnumField(
                        enum=djstripe.enums.ShippingRateTaxBehavior, max_length=11
                    ),
                ),
                (
                    "djstripe_owner_account",
                    djstripe.fields.StripeForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="djstripe.account",
                        to_field=settings.DJSTRIPE_FOREIGN_KEY_TO_FIELD,
                    ),
                ),
                (
                    "tax_code",
                    djstripe.fields.StripeForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="djstripe.taxcode",
                        to_field=settings.DJSTRIPE_FOREIGN_KEY_TO_FIELD,
                    ),
                ),
            ],
            options={
                "get_latest_by": "created",
                "verbose_name": "Shipping Rate",
            },
        ),
    ]
