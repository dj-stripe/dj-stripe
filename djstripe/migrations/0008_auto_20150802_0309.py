# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields


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
            model_name='event',
            name='event_timestamp',
            field=models.DateTimeField(help_text="Empty for old entries. For all others, this entry field gives the timestamp of the time when the event occured from Stripe's perspective. This is as opposed to the time when we received notice of the event, which is not guaranteed to be the same timeand which is recorded in a different field.", null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='received_api_version',
            field=models.CharField(help_text='the API version at which the event data was rendered. Blank for old entries only, all new entries will have this value', max_length=15, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='request_id',
            field=models.CharField(help_text="Information about the request that triggered this event, for traceability purposes. If empty string then this is an old entry without that data. If Null then this is not an old entry, but a Stripe 'automated' event with no associated request.", max_length=50, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='customer',
            field=models.ForeignKey(to='djstripe.Customer', help_text='In the event that there is a related customer, this will point to that Customer record', null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='kind',
            field=models.CharField(help_text="Stripe's event description code (called 'type' in their API)", max_length=250),
        ),
        migrations.AlterField(
            model_name='event',
            name='processed',
            field=models.BooleanField(default=False, help_text='If validity is performed, webhook event processor(s) may run to take further action on the event. Once these have run, this is set to True.'),
        ),
        migrations.AlterField(
            model_name='event',
            name='valid',
            field=models.NullBooleanField(help_text='Tri-state bool. Null == validity not yet confirmed. Otherwise, this field indicates that this event was checked via stripe api and found to be either authentic (valid=True) or in-authentic (possibly malicious)'),
        ),
        migrations.AlterField(
            model_name='event',
            name='webhook_message',
            field=jsonfield.fields.JSONField(default=dict, help_text='data received at webhook. data should be considered to be garbage until valididty check is run and valid flag is set'),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='date',
            field=models.DateTimeField(help_text='Date the transfer is scheduled to arrive at destination'),
        ),
    ]
