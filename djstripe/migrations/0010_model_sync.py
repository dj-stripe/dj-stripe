# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core import serializers
from django.db import migrations
from django.db.migrations.operations.special import RunPython
from tqdm import tqdm


def resync_subscriptions(apps, schema_editor):
    """
    Since subscription IDs were not previously stored, a direct migration will leave us
    with a bunch of orphaned objects. It was decided [here](https://github.com/pydanny/dj-stripe/issues/162)
    that a purge and re-sync would be the best option. No data that is currently available on stripe will
    be deleted. Anything stored locally will be purged.
    """

    # This is okay, since we're only doing a forward migration.
    from djstripe.models import Subscription

    import stripe
    stripe.api_version = "2016-03-07"

    if Subscription.objects.count():
        print("Purging subscriptions. Don't worry, all active subscriptions will be re-synced from stripe. Just in case you didn't get the memo, we'll print out a json representation of each object for your records:")
        print(serializers.serialize("json", Subscription.objects.all()))
        Subscription.objects.all().delete()

        print("Re-syncing subscriptions. This may take a while.")

        for stripe_subscription in tqdm(iterable=Subscription.api_list(), desc="Sync", unit=" subscriptions"):
            Subscription.sync_from_stripe_data(stripe_subscription)

        print("Subscription re-sync complete.")


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0009_auto_20160501_1838'),
    ]

    operations = [
        RunPython(resync_subscriptions),
    ]
