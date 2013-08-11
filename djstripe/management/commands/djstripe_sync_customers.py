from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from ...settings import User
from ...sync import sync_customer


class Command(BaseCommand):

    help = "Sync customer data with stripe"

    def handle(self, *args, **options):
        qs = User.objects.exclude(customer__isnull=True)
        count = 0
        total = qs.count()
        for user in qs:
            count += 1
            perc = int(round(100 * (float(count) / float(total))))
            print("[{0}/{1} {2}%] Syncing {3} [{4}]").format(
                count, total, perc, user.username, user.pk
            )
            sync_customer(user)
