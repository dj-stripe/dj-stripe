# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0007_auto_20150625_1243'),
    ]

    operations = [
        migrations.AlterField(
            model_name='plan',
            name='interval',
            field=models.CharField(max_length=10, verbose_name='Interval type', choices=[('day', 'Day'), ('week', 'Week'), ('month', 'Month'), ('year', 'Year')]),
        ),
    ]
