# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0009_auto_20150817_0646'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stripesource',
            name='customer',
            field=models.ForeignKey(to='djstripe.Customer', related_name='sources'),
            preserve_default=True,
        ),
    ]
