# Generated by Django 3.2.14 on 2022-08-22 16:42

from django.db import migrations

import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ("djstripe", "0013_auto_20220822_1634"),
    ]

    operations = [
        migrations.AlterField(
            model_name="charge",
            name="amount",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14
            ),
        ),
        migrations.AlterField(
            model_name="charge",
            name="amount_captured",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="charge",
            name="amount_refunded",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14
            ),
        ),
        migrations.AlterField(
            model_name="charge",
            name="application_fee_amount",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="coupon",
            name="amount_off",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="amount_due",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="amount_paid",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="amount_remaining",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="application_fee_amount",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="subtotal",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="tax",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="total",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14
            ),
        ),
        migrations.AlterField(
            model_name="invoiceitem",
            name="amount",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14
            ),
        ),
        migrations.AlterField(
            model_name="payout",
            name="amount",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14
            ),
        ),
        migrations.AlterField(
            model_name="plan",
            name="amount",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="source",
            name="amount",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="transfer",
            name="amount",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14
            ),
        ),
        migrations.AlterField(
            model_name="transfer",
            name="amount_reversed",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="upcominginvoice",
            name="amount_due",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14
            ),
        ),
        migrations.AlterField(
            model_name="upcominginvoice",
            name="amount_paid",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="upcominginvoice",
            name="amount_remaining",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="upcominginvoice",
            name="application_fee_amount",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="upcominginvoice",
            name="subtotal",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14
            ),
        ),
        migrations.AlterField(
            model_name="upcominginvoice",
            name="tax",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AlterField(
            model_name="upcominginvoice",
            name="total",
            field=djstripe.fields.StripeDecimalCurrencyAmountField(
                decimal_places=2, max_digits=14
            ),
        ),
    ]
