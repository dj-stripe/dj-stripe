# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from ...settings import get_subscriber_model
from ...sync import sync_subscriber


class Command(BaseCommand):

    help = "Sync subscriber data with stripe"

    def handle(self, *args, **options):
        qs = get_subscriber_model().objects.filter(customer__isnull=True)
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
