# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0007_auto_20150625_1243'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('stripe_id', models.CharField(unique=True, max_length=50)),
                ('plan', models.CharField(max_length=100)),
                ('quantity', models.IntegerField()),
                ('start', models.DateTimeField()),
                ('status', models.CharField(max_length=25)),
                ('cancel_at_period_end', models.BooleanField(default=False)),
                ('canceled_at', models.DateTimeField(null=True, blank=True)),
                ('current_period_end', models.DateTimeField(null=True)),
                ('current_period_start', models.DateTimeField(null=True)),
                ('ended_at', models.DateTimeField(null=True, blank=True)),
                ('trial_end', models.DateTimeField(null=True, blank=True)),
                ('trial_start', models.DateTimeField(null=True, blank=True)),
                ('amount', models.DecimalField(max_digits=7, decimal_places=2)),
                ('customer', models.ForeignKey(related_name='subscriptions', to='djstripe.Customer', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
