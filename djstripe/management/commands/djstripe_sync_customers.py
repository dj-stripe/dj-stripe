# -*- coding: utf-8 -*-
"""
.. module:: djstripe.management.commands.djstripe_sync_customers.

   :synopsis: dj-stripe - sync_customer command.

.. moduleauthor:: @kavdev, @pydanny, @shvechikov

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.management.base import BaseCommand

from ...settings import get_subscriber_model
from ...sync import sync_subscriber


class Command(BaseCommand):
    """Sync subscriber data with stripe."""

    help = "Sync subscriber data with stripe."

    def handle(self, *args, **options):
        """Call sync_subscriber on Subscribers without customers associated to them."""
        qs = get_subscriber_model().objects.filter(djstripe_customers__isnull=True)
        count = 0
        total = qs.count()
        for subscriber in qs:
            count += 1
            perc = int(round(100 * (float(count) / float(total))))
            print(
                "[{0}/{1} {2}%] Syncing {3} [{4}]".format(
                    count, total, perc, subscriber.email, subscriber.pk
                )
            )
            sync_subscriber(subscriber)
