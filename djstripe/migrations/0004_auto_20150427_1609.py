# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import jsonfield.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0003_auto_20150128_0800'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='webhook_message',
            field=jsonfield.fields.JSONField(),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='invoice',
            name='stripe_id',
            field=models.CharField(max_length=50, unique=True),
            preserve_default=True,
        ),
    ]
