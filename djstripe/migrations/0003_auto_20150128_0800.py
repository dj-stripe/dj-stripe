# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


# Can't use the callable because the app registry is not ready yet.
# Really trusting users here... bad idea? probably.
DJSTRIPE_UNSAFE_SUBSCRIBER_MODEL = getattr(settings, "DJSTRIPE_SUBSCRIBER_MODEL", settings.AUTH_USER_MODEL)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(DJSTRIPE_UNSAFE_SUBSCRIBER_MODEL),
        ('djstripe', '0002_auto_20150122_2000'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='subscriber',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to=DJSTRIPE_UNSAFE_SUBSCRIBER_MODEL),
            preserve_default=True,
        ),
    ]
