# Generated by Django 3.2.12 on 2022-03-29 17:40

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("djstripe", "0019_add_customer_discount"),
    ]

    operations = [
        migrations.AddField(
            model_name="payout",
            name="original_payout",
            field=models.OneToOneField(
                blank=True,
                help_text="If this payout reverses another, this is the ID of the original payout.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="djstripe.payout",
            ),
        ),
        migrations.AddField(
            model_name="payout",
            name="reversed_by",
            field=models.OneToOneField(
                blank=True,
                help_text="If this payout was reversed, this is the ID of the payout that reverses this payout.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reversed_payout",
                to="djstripe.payout",
            ),
        ),
    ]
