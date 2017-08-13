# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-22 04:28
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0024_auto_20170308_0757'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='account',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='charge',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='customer',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='customer',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='eventprocessingexception',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='eventprocessingexception',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='plan',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='stripesource',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='stripesource',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='modified',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
