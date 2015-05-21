# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0007_copy_subscriptions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='currentsubscription',
            name='customer',
        ),
        migrations.DeleteModel(
            name='CurrentSubscription',
        ),
    ]
