# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-22 20:07
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0029_customer_account'),
    ]

    operations = [
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('livemode', djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.')),
                ('stripe_timestamp', djstripe.fields.StripeDateTimeField(help_text='The datetime this object was created in stripe.', null=True)),
                ('metadata', djstripe.fields.StripeJSONField(blank=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.', null=True)),
                ('description', djstripe.fields.StripeTextField(blank=True, help_text='A description of this object.', null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('stripe_id', djstripe.fields.StripeIdField(max_length=500)),
                ('amount_off', djstripe.fields.StripeCurrencyField(blank=True, decimal_places=2, help_text='Amount that will be taken off the subtotal of any invoices for this customer.', max_digits=8, null=True)),
                ('currency', djstripe.fields.StripeCharField(blank=True, help_text='Three-letter ISO currency code', max_length=3, null=True)),
                ('duration', djstripe.fields.StripeCharField(choices=[('forever', 'Forever'), ('once', 'Once'), ('repeating', 'Repeating')], help_text='Describes how long a customer who applies this coupon will get the discount.', max_length=9)),
                ('duration_in_months', djstripe.fields.StripePositiveIntegerField(blank=True, help_text='If `duration` is `repeating`, the number of months the coupon applies.', null=True)),
                ('max_redemptions', djstripe.fields.StripePositiveIntegerField(blank=True, help_text='Maximum number of times this coupon can be redeemed, in total, before it is no longer valid.', null=True)),
                ('percent_off', djstripe.fields.StripePositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(100)])),
                ('redeem_by', djstripe.fields.StripeDateTimeField(blank=True, help_text='Date after which the coupon can no longer be redeemed. Max 5 years in the future.', null=True)),
                ('times_redeemed', djstripe.fields.StripePositiveIntegerField(default=0, editable=False, help_text='Number of times this coupon has been applied to a customer.')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterUniqueTogether(
            name='coupon',
            unique_together=set([('stripe_id', 'livemode')]),
        ),
    ]
