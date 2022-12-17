# Generated by Django 3.2.15 on 2022-12-17 05:59

from django.db import migrations

import djstripe.enums
import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ("djstripe", "0011_2_7"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentmethod",
            name="affirm",
            field=djstripe.fields.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="paymentmethod",
            name="blik",
            field=djstripe.fields.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="paymentmethod",
            name="customer_balance",
            field=djstripe.fields.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="paymentmethod",
            name="klarna",
            field=djstripe.fields.JSONField(blank=True, null=True),
        ),
    ]
