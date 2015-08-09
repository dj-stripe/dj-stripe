# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import djstripe.fields
import djstripe.models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0008_auto_20150806_1641'),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('stripe_id', djstripe.fields.StripeIdField(max_length=50, unique=True)),
                ('livemode', djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.')),
                ('metadata', djstripe.fields.StripeJSONField(blank=True, null=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.')),
                ('description', djstripe.fields.StripeTextField(blank=True, null=True, help_text='A description of this object.')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Card',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('stripe_id', djstripe.fields.StripeIdField(max_length=50, unique=True)),
                ('livemode', djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.')),
                ('metadata', djstripe.fields.StripeJSONField(blank=True, null=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.')),
                ('description', djstripe.fields.StripeTextField(blank=True, null=True, help_text='A description of this object.')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='charge',
            name='account',
            field=models.ForeignKey(default=djstripe.models._lazy_get_account_default, related_name='charges', to='djstripe.Account', help_text='The account (if any) the charge was made on behalf of.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='card',
            field=models.ForeignKey(related_name='charges', to='djstripe.Card', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='currency',
            field=djstripe.fields.StripeCharField(blank=True, max_length=3, help_text='Three-letter ISO currency code representing the currency in which the charge was made.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='failure_code',
            field=djstripe.fields.StripeCharField(blank=True, choices=[('invalid_number', 'Invalid Number'), ('invalid_expiry_month', 'Invalid Expiry Month'), ('invalid_expiry_year', 'Invalid Expiry Year'), ('invalid_cvc', 'Invalid Cvc'), ('incorrect_number', 'Incorrect Number'), ('expired_card', 'Expired Card'), ('incorrect_cvc', 'Incorrect Cvc'), ('incorrect_zip', 'Incorrect Zip'), ('card_declined', 'Card Declined'), ('missing', 'Missing'), ('processing_error', 'Processing Error'), ('rate_limit', 'Rate Limit')], max_length=30, help_text='Error code explaining reason for charge failure if available.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='failure_message',
            field=djstripe.fields.StripeTextField(blank=True, help_text='Message to user further explaining reason for charge failure if available.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='fraudulent',
            field=djstripe.fields.StripeNullBooleanField(help_text='Whether or not this charge was marked as fraudulent.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, null=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='shipping',
            field=djstripe.fields.StripeJSONField(blank=True, help_text='Shipping information for the charge'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='source_stripe_id',
            field=djstripe.fields.StripeIdField(blank=True, max_length=50, help_text='The payment source id.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='source_type',
            field=djstripe.fields.StripeCharField(blank=True, max_length=20, help_text='The payment source type. If the payment source is supported by dj-stripe, a corresponding model is attached to this Charge via a foreign key matching this field.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='status',
            field=djstripe.fields.StripeCharField(blank=True, choices=[('succeeded', 'Succeeded'), ('failed', 'Failed')], max_length=10, help_text='The status of the payment is either ``succeeded`` or ``failed``.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='transfer',
            field=models.ForeignKey(to='djstripe.Transfer', null=True, help_text='The transfer to the destination account (only applicable if the charge was created using the destination parameter).'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='customer',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, null=True, help_text='A description of this object.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='customer',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, null=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, null=True, help_text='A description of this object.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, null=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, null=True, help_text='A description of this object.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, null=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='plan',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, null=True, help_text='A description of this object.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='plan',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, null=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='transfer',
            name='metadata',
            field=djstripe.fields.StripeJSONField(blank=True, null=True, help_text='A set of key/value pairs that you can attach to an object. It can be useful for storing additional information about an object in a structured format.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='amount',
            field=djstripe.fields.StripeCurrencyField(decimal_places=2, max_digits=7, null=True, help_text='Amount charged.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='amount_refunded',
            field=djstripe.fields.StripeCurrencyField(decimal_places=2, max_digits=7, null=True, help_text='Amount refunded (can be less than the amount attribute on the charge if a partial refund was issued).'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='captured',
            field=djstripe.fields.StripeNullBooleanField(help_text='If the charge was created without capturing, this boolean represents whether or not it is still uncaptured or has since been captured.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='card_kind',
            field=djstripe.fields.StripeCharField(blank=True, max_length=50, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='card_last_4',
            field=djstripe.fields.StripeCharField(blank=True, max_length=4, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='charge_created',
            field=djstripe.fields.StripeDateTimeField(null=True, help_text='The datetime this object was created.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='customer',
            field=models.ForeignKey(related_name='charges', to='djstripe.Customer', help_text='The customer associated with this charge.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, null=True, help_text='A description of this object.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='disputed',
            field=djstripe.fields.StripeNullBooleanField(help_text='Whether or not this charge is disputed.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='invoice',
            field=models.ForeignKey(related_name='charges', to='djstripe.Invoice', null=True, help_text='The invoice associated with this charge, if it exists.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='paid',
            field=djstripe.fields.StripeNullBooleanField(help_text='``true`` if the charge succeeded, or was successfully authorized for later capture, ``false`` otherwise.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='receipt_sent',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='refunded',
            field=djstripe.fields.StripeNullBooleanField(help_text='Whether or not the charge has been fully refunded. If the charge is only partially refunded, this attribute will still be false.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='customer',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='event_timestamp',
            field=djstripe.fields.StripeDateTimeField(null=True, help_text="Empty for old entries. For all others, this entry field gives the timestamp of the time when the event occured from Stripe's perspective. This is as opposed to the time when we received notice of the event, which is not guaranteed to be the same timeand which is recorded in a different field."),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='kind',
            field=djstripe.fields.StripeCharField(max_length=250, help_text="Stripe's event description code"),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='received_api_version',
            field=djstripe.fields.StripeCharField(blank=True, max_length=15, help_text='the API version at which the event data was rendered. Blank for old entries only, all new entries will have this value'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='request_id',
            field=djstripe.fields.StripeCharField(blank=True, max_length=50, null=True, help_text="Information about the request that triggered this event, for traceability purposes. If empty string then this is an old entry without that data. If Null then this is not an old entry, but a Stripe 'automated' event with no associated request."),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='event',
            name='webhook_message',
            field=djstripe.fields.StripeJSONField(help_text='data received at webhook. data should be considered to be garbage until validity check is run and valid flag is set'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='charge',
            field=djstripe.fields.StripeIdField(default='', blank=True, max_length=50, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='plan',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='transfer',
            name='date',
            field=djstripe.fields.StripeDateTimeField(help_text='Date the transfer is scheduled to arrive at destination'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='transfer',
            name='description',
            field=djstripe.fields.StripeTextField(blank=True, null=True, help_text='A description of this object.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='transfer',
            name='livemode',
            field=djstripe.fields.StripeNullBooleanField(default=False, help_text='Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
            preserve_default=True,
        ),
    ]
