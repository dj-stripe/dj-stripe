# Generated by Django 3.2.13 on 2022-05-27 17:06

from django.db import migrations
import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0017_auto_20220524_1836'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='amount_due',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='amount_paid',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(null=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='amount_remaining',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(null=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='application_fee_amount',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='subtotal',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='tax',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='total',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(verbose_name='Total (in cents) after discount.'),
        ),
        migrations.AlterField(
            model_name='upcominginvoice',
            name='amount_due',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(),
        ),
        migrations.AlterField(
            model_name='upcominginvoice',
            name='amount_paid',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(null=True),
        ),
        migrations.AlterField(
            model_name='upcominginvoice',
            name='amount_remaining',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(null=True),
        ),
        migrations.AlterField(
            model_name='upcominginvoice',
            name='application_fee_amount',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='upcominginvoice',
            name='subtotal',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(),
        ),
        migrations.AlterField(
            model_name='upcominginvoice',
            name='tax',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='upcominginvoice',
            name='total',
            field=djstripe.fields.StripeQuantumCurrencyAmountField(verbose_name='Total (in cents) after discount.'),
        ),
    ]
