# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0006_auto_20150602_1934'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='currentsubscription',
            name='plan',
        ),
        migrations.RemoveField(
            model_name='invoiceitem',
            name='plan',
        ),
    ]
