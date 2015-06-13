# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0007_auto_20150613_2326'),
    ]

    operations = [
        migrations.AddField(
            model_name='currentsubscription',
            name='plan',
            field=models.ForeignKey(related_name='current_subscription', blank=True, to='djstripe.Plan', null=True),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='plan',
            field=models.ForeignKey(related_name='invoice_item', blank=True, to='djstripe.Plan', null=True),
        ),
    ]
