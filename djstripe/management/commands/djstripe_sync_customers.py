from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from djstripe.backends import get_backend


class Command(BaseCommand):

    help = "Sync customer data with stripe"

    def handle(self, *args, **options):
        backend = get_backend()   
        backend.sync_customers(*args, **options)
