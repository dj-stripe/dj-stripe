# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0011_auto_20150809_2046'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transfer',
            name='event',
            field=models.ForeignKey(to='djstripe.Event', related_name='transfers', null=True),
            preserve_default=True,
        ),
    ]
