# Generated by Django 3.2.10 on 2021-12-27 21:38

import django.core.validators
from django.db import migrations

import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ("djstripe", "0015_alter_customer_delinquent"),
    ]

    operations = [
        migrations.AlterField(
            model_name="taxrate",
            name="percentage",
            field=djstripe.fields.StripePercentField(
                decimal_places=4,
                help_text="This represents the tax rate percent out of 100.",
                max_digits=7,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(100),
                ],
            ),
        ),
    ]
