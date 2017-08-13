# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0006_auto_20150602_1934'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='card_exp_month',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='card_exp_year',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
    ]
