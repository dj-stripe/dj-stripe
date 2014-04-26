from __future__ import unicode_literals
from django.core.management.base import BaseCommand

from djstripe.backends import get_backend

class Command(BaseCommand):

    help = "Make sure your Stripe account has the plans"

    def handle(self, *args, **options):
        backend = get_backend()      
        backend.sync_plans(*args, **options)
