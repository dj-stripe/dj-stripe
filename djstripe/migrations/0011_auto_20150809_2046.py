# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0010_auto_20150809_2043'),
    ]

    operations = [
        migrations.RenameField(
            model_name='event',
            old_name='kind',
            new_name='type',
        ),
    ]
