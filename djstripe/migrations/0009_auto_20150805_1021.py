# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0008_auto_20150802_0309'),
    ]

    operations = [
        migrations.AddField(
            model_name='charge',
            name='livemode',
            field=models.NullBooleanField(default=False, help_text=b'Null here indicates that data was unavailable. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='customer',
            name='livemode',
            field=models.NullBooleanField(default=False, help_text=b'Null here indicates that data was unavailable. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='livemode',
            field=models.NullBooleanField(default=False, help_text=b'Null here indicates that data was unavailable. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='plan',
            name='livemode',
            field=models.NullBooleanField(default=False, help_text=b'Null here indicates that data was unavailable. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AddField(
            model_name='transfer',
            name='livemode',
            field=models.NullBooleanField(default=False, help_text=b'Null here indicates that data was unavailable. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
        migrations.AlterField(
            model_name='event',
            name='livemode',
            field=models.NullBooleanField(default=False, help_text=b'Null here indicates that data was unavailable. Otherwise, this field indicates whether this record comes from Stripe test mode or live mode operation.'),
        ),
    ]
