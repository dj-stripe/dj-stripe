# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('djstripe', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DJStripeCustomer',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(verbose_name='created', editable=False, default=django.utils.timezone.now)),
                ('modified', model_utils.fields.AutoLastModifiedField(verbose_name='modified', editable=False, default=django.utils.timezone.now)),
                ('stripe_id', models.CharField(max_length=50, unique=True)),
                ('card_fingerprint', models.CharField(blank=True, max_length=200)),
                ('card_last_4', models.CharField(blank=True, max_length=4)),
                ('card_kind', models.CharField(blank=True, max_length=50)),
                ('date_purged', models.DateTimeField(null=True, editable=False)),
                ('customer', models.OneToOneField(null=True, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='customer',
            name='user',
        ),
        migrations.RemoveField(
            model_name='charge',
            name='customer',
        ),
        migrations.RemoveField(
            model_name='currentsubscription',
            name='customer',
        ),
        migrations.RemoveField(
            model_name='event',
            name='customer',
        ),
        migrations.RemoveField(
            model_name='invoice',
            name='customer',
        ),
        migrations.DeleteModel(
            name='Customer',
        ),
        migrations.AddField(
            model_name='charge',
            name='djstripecustomer',
            field=models.ForeignKey(default=0, to='djstripe.DJStripeCustomer', related_name='charges'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='currentsubscription',
            name='djstripecustomer',
            field=models.OneToOneField(related_name='current_subscription', null=True, to='djstripe.DJStripeCustomer'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='djstripecustomer',
            field=models.ForeignKey(null=True, to='djstripe.DJStripeCustomer'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='djstripecustomer',
            field=models.ForeignKey(default=0, to='djstripe.DJStripeCustomer', related_name='invoices'),
            preserve_default=False,
        ),
    ]
