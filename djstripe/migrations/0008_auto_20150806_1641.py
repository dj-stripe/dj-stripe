# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import djstripe.stripe_objects


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0007_auto_20150625_1243'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='validated_message',
        ),
        migrations.AddField(
            model_name='charge',
            name='livemode',
            field=djstripe.stripe_objects.StripeNullBooleanField(default=False, help_text=b'Null here indicates that data was unavailable. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='customer',
            name='livemode',
            field=djstripe.stripe_objects.StripeNullBooleanField(default=False, help_text=b'Null here indicates that data was unavailable. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='event',
            name='event_timestamp',
            field=djstripe.stripe_objects.StripeDateTimeField(help_text=b"Empty for old entries. For all others, this entry field gives the timestamp of the time when the event occured from Stripe's perspective. This is as opposed to the time when we received notice of the event, which is not guaranteed to be the same timeand which is recorded in a different field.", null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='received_api_version',
            field=djstripe.stripe_objects.StripeCharField(help_text=b'the API version at which the event data was rendered. Blank for old entries only, all new entries will have this value', max_length=15, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='request_id',
            field=djstripe.stripe_objects.StripeCharField(help_text=b"Information about the request that triggered this event, for traceability purposes. If empty string then this is an old entry without that data. If Null then this is not an old entry, but a Stripe 'automated' event with no associated request.", max_length=50, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='livemode',
            field=djstripe.stripe_objects.StripeNullBooleanField(default=False, help_text=b'Null here indicates that data was unavailable. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='plan',
            name='livemode',
            field=djstripe.stripe_objects.StripeNullBooleanField(default=False, help_text=b'Null here indicates that data was unavailable. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='livemode',
            field=djstripe.stripe_objects.StripeNullBooleanField(default=False, help_text=b'Null here indicates that data was unavailable. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AlterField(
            model_name='charge',
            name='amount',
            field=djstripe.stripe_objects.StripeCurrencyField(null=True, max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='charge',
            name='amount_refunded',
            field=djstripe.stripe_objects.StripeCurrencyField(null=True, max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='charge',
            name='captured',
            field=djstripe.stripe_objects.StripeNullBooleanField(),
        ),
        migrations.AlterField(
            model_name='charge',
            name='card_kind',
            field=djstripe.stripe_objects.StripeCharField(max_length=50, blank=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='card_last_4',
            field=djstripe.stripe_objects.StripeCharField(max_length=4, blank=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='charge_created',
            field=djstripe.stripe_objects.StripeDateTimeField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='description',
            field=djstripe.stripe_objects.StripeTextField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='disputed',
            field=djstripe.stripe_objects.StripeNullBooleanField(),
        ),
        migrations.AlterField(
            model_name='charge',
            name='fee',
            field=djstripe.stripe_objects.StripeCurrencyField(null=True, max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='charge',
            name='paid',
            field=djstripe.stripe_objects.StripeNullBooleanField(),
        ),
        migrations.AlterField(
            model_name='charge',
            name='receipt_sent',
            field=djstripe.stripe_objects.StripeNullBooleanField(default=None),
        ),
        migrations.AlterField(
            model_name='charge',
            name='refunded',
            field=djstripe.stripe_objects.StripeNullBooleanField(),
        ),
        migrations.AlterField(
            model_name='charge',
            name='stripe_id',
            field=djstripe.stripe_objects.StripeIdField(unique=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='customer',
            name='card_exp_month',
            field=djstripe.stripe_objects.StripePositiveIntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='customer',
            name='card_exp_year',
            field=djstripe.stripe_objects.StripePositiveIntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='customer',
            name='card_fingerprint',
            field=djstripe.stripe_objects.StripeCharField(max_length=200, blank=True),
        ),
        migrations.AlterField(
            model_name='customer',
            name='card_kind',
            field=djstripe.stripe_objects.StripeCharField(max_length=50, blank=True),
        ),
        migrations.AlterField(
            model_name='customer',
            name='card_last_4',
            field=djstripe.stripe_objects.StripeCharField(max_length=4, blank=True),
        ),
        migrations.AlterField(
            model_name='customer',
            name='stripe_id',
            field=djstripe.stripe_objects.StripeIdField(unique=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='event',
            name='customer',
            field=models.ForeignKey(to='djstripe.Customer', help_text='In the event that there is a related customer, this will point to that Customer record', null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='kind',
            field=djstripe.stripe_objects.StripeCharField(help_text=b"Stripe's event description code", max_length=250),
        ),
        migrations.AlterField(
            model_name='event',
            name='livemode',
            field=djstripe.stripe_objects.StripeNullBooleanField(default=False, help_text=b'Null here indicates that data was unavailable. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AlterField(
            model_name='event',
            name='processed',
            field=models.BooleanField(default=False, help_text='If validity is performed, webhook event processor(s) may run to take further action on the event. Once these have run, this is set to True.'),
        ),
        migrations.AlterField(
            model_name='event',
            name='stripe_id',
            field=djstripe.stripe_objects.StripeIdField(unique=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='event',
            name='valid',
            field=models.NullBooleanField(help_text='Tri-state bool. Null == validity not yet confirmed. Otherwise, this field indicates that this event was checked via stripe api and found to be either authentic (valid=True) or in-authentic (possibly malicious)'),
        ),
        migrations.AlterField(
            model_name='event',
            name='webhook_message',
            field=djstripe.stripe_objects.StripeJSONField(default=dict, help_text=b'data received at webhook. data should be considered to be garbage until validity check is run and valid flag is set'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='attempted',
            field=djstripe.stripe_objects.StripeNullBooleanField(),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='attempts',
            field=djstripe.stripe_objects.StripePositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='charge',
            field=djstripe.stripe_objects.StripeIdField(default=b'', max_length=50, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='closed',
            field=djstripe.stripe_objects.StripeBooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='date',
            field=djstripe.stripe_objects.StripeDateTimeField(),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='paid',
            field=djstripe.stripe_objects.StripeBooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='period_end',
            field=djstripe.stripe_objects.StripeDateTimeField(),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='period_start',
            field=djstripe.stripe_objects.StripeDateTimeField(),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='stripe_id',
            field=djstripe.stripe_objects.StripeIdField(unique=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='subtotal',
            field=djstripe.stripe_objects.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='total',
            field=djstripe.stripe_objects.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='plan',
            name='stripe_id',
            field=djstripe.stripe_objects.StripeIdField(unique=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='adjustment_count',
            field=djstripe.stripe_objects.StripeIntegerField(),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='adjustment_fees',
            field=djstripe.stripe_objects.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='adjustment_gross',
            field=djstripe.stripe_objects.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='amount',
            field=djstripe.stripe_objects.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='charge_count',
            field=djstripe.stripe_objects.StripeIntegerField(),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='charge_fees',
            field=djstripe.stripe_objects.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='charge_gross',
            field=djstripe.stripe_objects.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='collected_fee_count',
            field=djstripe.stripe_objects.StripeIntegerField(),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='collected_fee_gross',
            field=djstripe.stripe_objects.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='date',
            field=djstripe.stripe_objects.StripeDateTimeField(help_text=b'Date the transfer is scheduled to arrive at destination'),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='description',
            field=djstripe.stripe_objects.StripeTextField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='net',
            field=djstripe.stripe_objects.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='refund_count',
            field=djstripe.stripe_objects.StripeIntegerField(),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='refund_fees',
            field=djstripe.stripe_objects.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='refund_gross',
            field=djstripe.stripe_objects.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='status',
            field=djstripe.stripe_objects.StripeCharField(max_length=25),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='stripe_id',
            field=djstripe.stripe_objects.StripeIdField(unique=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='validation_count',
            field=djstripe.stripe_objects.StripeIntegerField(),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='validation_fees',
            field=djstripe.stripe_objects.StripeCurrencyField(max_digits=7, decimal_places=2),
        ),
    ]
