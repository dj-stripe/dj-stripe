# Generated by Django 2.0.8 on 2019-01-30 13:02

from django.db import migrations
import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0002_auto_20180627_1121'),
    ]

    operations = [
        migrations.AlterField(
            model_name='plan',
            name='amount',
            field=djstripe.fields.StripeCurrencyField(decimal_places=2, help_text='Amount to be charged on the interval specified.', max_digits=8, null=True),
        ),
    ]
