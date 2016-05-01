# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core import serializers
from django.db import migrations
from django.db.migrations.operations.special import RunPython
import tqdm

from djstripe.utils import simple_stripe_pagination_iterator


def resync_subscriptions(apps, schema_editor):
    """
    Since subscription IDs were not previously stored, a direct migration will leave us
    with a bunch of orphaned objects. It was decided [here](https://github.com/pydanny/dj-stripe/issues/162)
    that a purge and re-sync would be the best option. No data that is currently available on stripe will
    be deleted. Anything stored locally will be purged.
    """

    from django.conf import settings
    import stripe
    stripe.api_version = "2015-07-28"

    Customer = apps.get_model('djstripe', 'Customer')
    Subscription = apps.get_model('djstripe', 'Subscription')

    if Subscription.objects.count():
        print("Purging subscriptions. Don't worry, all active subscriptions will be re-synced from stripe. Just in case you didn't get the memo, we'll print out a json representation of each object for your records:")
        print(serializers.serialize("json", Subscription.objects.all()))
        Subscription.objects.all().delete()

        print("Re-syncing subscriptions. This may take a while.")

        for customer in tqdm(iterable=Customer.objects.all(), desc="Sync", unit=" customers"):
            customer_stripe_subscriptions = customer.api_retrieve(api_key=settings.STRIPE_SECRET_KEY).subscriptions

            for stripe_subscription in simple_stripe_pagination_iterator(customer_stripe_subscriptions):
                Subscription.sync_from_stripe_data(stripe_subscription)

        print("Subscription re-sync complete.")


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0009_auto_20160501_1838'),
    ]

    operations = [
        RunPython(resync_subscriptions),
    ]
