# Generated by Django 4.2.16 on 2024-12-03 11:46

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import djstripe.fields


class Migration(migrations.Migration):
    dependencies = [
        ("djstripe", "0013_2_9"),
    ]

    operations = [
        migrations.RemoveField(model_name="taxid", name="verification"),
        migrations.AlterField(
            model_name="taxid",
            name="customer",
            field=djstripe.fields.StripeForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tax_ids",
                to="djstripe.customer",
                to_field=settings.DJSTRIPE_FOREIGN_KEY_TO_FIELD,
            ),
        ),
        migrations.AlterField(
            model_name="webhookendpoint",
            name="api_version",
            field=models.CharField(
                blank=True,
                help_text="The API version events are rendered as for this webhook endpoint. Defaults to the configured Stripe API Version.",
                max_length=64,
            ),
        ),
    ]