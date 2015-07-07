# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def copy_subscriptions_forwards(apps, schema_editor):
    from django.conf import settings
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    # Must have a sufficiently old API version to access "subscription", as against "subscriptions".
    stripe.api_version = "2012-11-07"

    CurrentSubscription = apps.get_model("djstripe", "CurrentSubscription")
    Subscription = apps.get_model("djstripe", "Subscription")
    num_skipped_ids = 0
    for csub in CurrentSubscription.objects.all():
        try:
            stripe_id = stripe.Customer.retrieve(csub.customer.stripe_id).subscription.id
        except:
            num_skipped_ids += 1
            stripe_id = "can_{:014d}".format(num_skipped_ids)

        sub = Subscription(created=csub.created,
                           modified=csub.modified,      # will get set to now() upon saving
                           stripe_id=stripe_id,
                           customer=csub.customer,
                           plan=csub.plan,
                           quantity=csub.quantity,
                           start=csub.start,
                           status=csub.status,
                           cancel_at_period_end=csub.cancel_at_period_end,
                           canceled_at=csub.canceled_at,
                           current_period_end=csub.current_period_end,
                           current_period_start=csub.current_period_start,
                           ended_at=csub.ended_at,
                           trial_end=csub.trial_end,
                           trial_start=csub.trial_start,
                           amount=csub.amount)
        sub.save()
    if num_skipped_ids > 0:
        print("Warning: unable to retrieve all {} subscription IDs, will be set to dummy values.".format(num_skipped_ids))


def copy_subscriptions_backwards(apps, schema_editor):
    CurrentSubscription = apps.get_model("djstripe", "CurrentSubscription")
    Subscription = apps.get_model("djstripe", "Subscription")
    for sub in Subscription.objects.all():
        try:
            csub = CurrentSubscription(created=sub.created,
                                       modified=sub.modified,      # will get set to now() upon saving
                                       customer=sub.customer,
                                       plan=sub.plan,
                                       quantity=sub.quantity,
                                       start=sub.start,
                                       status=sub.status,
                                       cancel_at_period_end=sub.cancel_at_period_end,
                                       canceled_at=sub.canceled_at,
                                       current_period_end=sub.current_period_end,
                                       current_period_start=sub.current_period_start,
                                       ended_at=sub.ended_at,
                                       trial_end=sub.trial_end,
                                       trial_start=sub.trial_start,
                                       amount=sub.amount)
            csub.save()
        except:
            # May throw if multiple subscriptions for a customer.
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('djstripe', '0008_add_subscription'),
    ]

    operations = [
        migrations.RunPython(copy_subscriptions_forwards,
                             copy_subscriptions_backwards),
    ]
