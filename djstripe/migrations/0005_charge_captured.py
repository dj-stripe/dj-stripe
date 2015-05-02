# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0004_auto_20150427_1609'),
    ]

    operations = [
        migrations.AddField(
            model_name='charge',
            name='captured',
            field=models.NullBooleanField(),
            preserve_default=True,
        ),
    ]
