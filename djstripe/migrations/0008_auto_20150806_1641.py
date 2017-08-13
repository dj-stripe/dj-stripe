# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0007_auto_20150625_1243'),
    ]

    operations = [
        migrations.RenameField(
            model_name='charge',
            old_name='charge_created',
            new_name='stripe_timestamp',
        ),
        migrations.RenameField(
            model_name='event',
            old_name='kind',
            new_name='type',
        ),
        migrations.RenameField(
            model_name='invoice',
            old_name='attempts',
            new_name='attempt_count',
        ),
        migrations.RenameModel(
            old_name='CurrentSubscription',
            new_name='Subscription',
        ),
    ]
