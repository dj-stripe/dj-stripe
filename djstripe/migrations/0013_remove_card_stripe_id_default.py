# Generated by Django 2.0 on 2017-12-03 01:21

from django.db import migrations
import djstripe.fields


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0012_card_customer_from_source'),
    ]

    operations = [
        migrations.AlterField(
            model_name='card',
            name='stripe_id',
            field=djstripe.fields.StripeIdField(max_length=255, unique=True),
        ),
    ]
