# Generated by Django 5.0.3 on 2024-04-17 11:03

import djstripe.enums
import djstripe.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("djstripe", "0012_2_8"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentintent",
            name="capture_method",
            field=djstripe.fields.StripeEnumField(
                enum=djstripe.enums.CaptureMethod, max_length=15
            ),
        ),
    ]
