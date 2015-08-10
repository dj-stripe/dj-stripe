# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0012_auto_20150810_0513'),
    ]

    operations = [
        migrations.AlterField(
            model_name='charge',
            name='currency',
            field=djstripe.fields.StripeCharField(null=True, max_length=3, help_text='Three-letter ISO currency code representing the currency in which the charge was made.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='failure_code',
            field=djstripe.fields.StripeCharField(choices=[('invalid_number', 'Invalid Number'), ('invalid_expiry_month', 'Invalid Expiry Month'), ('invalid_expiry_year', 'Invalid Expiry Year'), ('invalid_cvc', 'Invalid Cvc'), ('incorrect_number', 'Incorrect Number'), ('expired_card', 'Expired Card'), ('incorrect_cvc', 'Incorrect Cvc'), ('incorrect_zip', 'Incorrect Zip'), ('card_declined', 'Card Declined'), ('missing', 'Missing'), ('processing_error', 'Processing Error'), ('rate_limit', 'Rate Limit')], null=True, max_length=30, help_text='Error code explaining reason for charge failure if available.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='failure_message',
            field=djstripe.fields.StripeTextField(null=True, help_text='Message to user further explaining reason for charge failure if available.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='source_stripe_id',
            field=djstripe.fields.StripeIdField(null=True, max_length=50, help_text='The payment source id.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='source_type',
            field=djstripe.fields.StripeCharField(null=True, max_length=20, help_text='The payment source type. If the payment source is supported by dj-stripe, a corresponding model is attached to this Charge via a foreign key matching this field.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='status',
            field=djstripe.fields.StripeCharField(choices=[('succeeded', 'Succeeded'), ('failed', 'Failed')], null=True, max_length=10, help_text='The status of the payment is either ``succeeded`` or ``failed``.'),
            preserve_default=True,
        ),
    ]
