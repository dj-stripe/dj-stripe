# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0005_charge_captured'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoiceitem',
            name='plan',
            field=models.CharField(max_length=100, null=True, blank=True),
            preserve_default=True,
        ),
    ]
