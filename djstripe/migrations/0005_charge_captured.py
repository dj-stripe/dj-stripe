# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from django.db import migrations, models


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
