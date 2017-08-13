# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import, division, print_function, unicode_literals
)

import django.db.models.deletion
import django.utils.timezone
import jsonfield.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Charge',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('stripe_id', models.CharField(unique=True, max_length=50)),
                ('card_last_4', models.CharField(max_length=4, blank=True)),
                ('card_kind', models.CharField(max_length=50, blank=True)),
                ('amount', models.DecimalField(null=True, max_digits=7, decimal_places=2)),
                ('amount_refunded', models.DecimalField(null=True, max_digits=7, decimal_places=2)),
                ('description', models.TextField(blank=True)),
                ('paid', models.NullBooleanField()),
                ('disputed', models.NullBooleanField()),
                ('refunded', models.NullBooleanField()),
                ('fee', models.DecimalField(null=True, max_digits=7, decimal_places=2)),
                ('receipt_sent', models.BooleanField(default=False)),
                ('charge_created', models.DateTimeField(null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CurrentSubscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
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
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('stripe_id', models.CharField(unique=True, max_length=50)),
                ('card_fingerprint', models.CharField(max_length=200, blank=True)),
                ('card_last_4', models.CharField(max_length=4, blank=True)),
                ('card_kind', models.CharField(max_length=50, blank=True)),
                ('date_purged', models.DateTimeField(null=True, editable=False)),
                ('user', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('stripe_id', models.CharField(unique=True, max_length=50)),
                ('kind', models.CharField(max_length=250)),
                ('livemode', models.BooleanField(default=False)),
                ('webhook_message', jsonfield.fields.JSONField(default=dict)),
                ('validated_message', jsonfield.fields.JSONField(null=True)),
                ('valid', models.NullBooleanField()),
                ('processed', models.BooleanField(default=False)),
                ('customer', models.ForeignKey(to='djstripe.Customer', on_delete=django.db.models.deletion.CASCADE, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EventProcessingException',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('data', models.TextField()),
                ('message', models.CharField(max_length=500)),
                ('traceback', models.TextField()),
                ('event', models.ForeignKey(to='djstripe.Event', on_delete=django.db.models.deletion.CASCADE, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('stripe_id', models.CharField(max_length=50)),
                ('attempted', models.NullBooleanField()),
                ('attempts', models.PositiveIntegerField(null=True)),
                ('closed', models.BooleanField(default=False)),
                ('paid', models.BooleanField(default=False)),
                ('period_end', models.DateTimeField()),
                ('period_start', models.DateTimeField()),
                ('subtotal', models.DecimalField(max_digits=7, decimal_places=2)),
                ('total', models.DecimalField(max_digits=7, decimal_places=2)),
                ('date', models.DateTimeField()),
                ('charge', models.CharField(max_length=50, blank=True)),
                ('customer', models.ForeignKey(related_name='invoices', on_delete=django.db.models.deletion.CASCADE, to='djstripe.Customer')),
            ],
            options={
                'ordering': ['-date'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InvoiceItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('stripe_id', models.CharField(max_length=50)),
                ('amount', models.DecimalField(max_digits=7, decimal_places=2)),
                ('currency', models.CharField(max_length=10)),
                ('period_start', models.DateTimeField()),
                ('period_end', models.DateTimeField()),
                ('proration', models.BooleanField(default=False)),
                ('line_type', models.CharField(max_length=50)),
                ('description', models.CharField(max_length=200, blank=True)),
                ('plan', models.CharField(max_length=100, blank=True)),
                ('quantity', models.IntegerField(null=True)),
                ('invoice', models.ForeignKey(related_name='items', on_delete=django.db.models.deletion.CASCADE, to='djstripe.Invoice')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('stripe_id', models.CharField(unique=True, max_length=50)),
                ('name', models.CharField(max_length=100)),
                ('currency', models.CharField(max_length=10, choices=[('usd', 'U.S. Dollars'),
                                                                      ('gbp', 'Pounds (GBP)'), ('eur', 'Euros')])),
                ('interval', models.CharField(max_length=10, verbose_name='Interval type',
                                              choices=[('week', 'Week'), ('month', 'Month'), ('year', 'Year')])),
                ('interval_count', models.IntegerField(default=1, null=True,
                                                       verbose_name='Intervals between charges')),
                ('amount', models.DecimalField(verbose_name='Amount (per period)', max_digits=7, decimal_places=2)),
                ('trial_period_days', models.IntegerField(null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Transfer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('stripe_id', models.CharField(unique=True, max_length=50)),
                ('amount', models.DecimalField(max_digits=7, decimal_places=2)),
                ('status', models.CharField(max_length=25)),
                ('date', models.DateTimeField()),
                ('description', models.TextField(null=True, blank=True)),
                ('adjustment_count', models.IntegerField()),
                ('adjustment_fees', models.DecimalField(max_digits=7, decimal_places=2)),
                ('adjustment_gross', models.DecimalField(max_digits=7, decimal_places=2)),
                ('charge_count', models.IntegerField()),
                ('charge_fees', models.DecimalField(max_digits=7, decimal_places=2)),
                ('charge_gross', models.DecimalField(max_digits=7, decimal_places=2)),
                ('collected_fee_count', models.IntegerField()),
                ('collected_fee_gross', models.DecimalField(max_digits=7, decimal_places=2)),
                ('net', models.DecimalField(max_digits=7, decimal_places=2)),
                ('refund_count', models.IntegerField()),
                ('refund_fees', models.DecimalField(max_digits=7, decimal_places=2)),
                ('refund_gross', models.DecimalField(max_digits=7, decimal_places=2)),
                ('validation_count', models.IntegerField()),
                ('validation_fees', models.DecimalField(max_digits=7, decimal_places=2)),
                ('event', models.ForeignKey(related_name='transfers', on_delete=django.db.models.deletion.CASCADE, to='djstripe.Event')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TransferChargeFee',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', models.DateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('amount', models.DecimalField(max_digits=7, decimal_places=2)),
                ('application', models.TextField(null=True, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
                ('kind', models.CharField(max_length=150)),
                ('transfer', models.ForeignKey(related_name='charge_fee_details', on_delete=django.db.models.deletion.CASCADE, to='djstripe.Transfer')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='currentsubscription',
            name='customer',
            field=models.OneToOneField(related_name='current_subscription', on_delete=django.db.models.deletion.CASCADE, null=True, to='djstripe.Customer'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='customer',
            field=models.ForeignKey(related_name='charges', on_delete=django.db.models.deletion.CASCADE, to='djstripe.Customer'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='invoice',
            field=models.ForeignKey(related_name='charges', on_delete=django.db.models.deletion.CASCADE, to='djstripe.Invoice', null=True),
            preserve_default=True,
        ),
    ]
