# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0009_auto_20150809_2042'),
    ]

    operations = [
        migrations.RenameField(
            model_name='charge',
            old_name='charge_created',
            new_name='created_stripe',
        ),
    ]
