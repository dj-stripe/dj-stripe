# Generated by Django 4.0.1 on 2022-01-14 18:11

from django.db import migrations

import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ("djstripe", "0015_alter_payout_failure_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="pause_collection",
            field=djstripe.fields.JSONField(blank=True, null=True),
        ),
    ]
