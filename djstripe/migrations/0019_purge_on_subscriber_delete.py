# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-28 00:48
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
from django.db.models.deletion import SET_NULL


DJSTRIPE_SUBSCRIBER_MODEL = getattr(settings, "DJSTRIPE_SUBSCRIBER_MODEL", settings.AUTH_USER_MODEL)


def on_subscriber_delete_purge_customers(collector, field, sub_objs, using):
    """ Ensure that all customers attached to subscriber are purged on deletion. """
    for obj in sub_objs:
        obj.purge()

    SET_NULL(collector, field, sub_objs, using)



class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0018_field_docs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='subscriber',
            field=models.OneToOneField(null=True, on_delete=on_subscriber_delete_purge_customers, to=DJSTRIPE_SUBSCRIBER_MODEL),
        ),
    ]
