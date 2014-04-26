from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from djstripe.backends import get_backend

class Command(BaseCommand):

    help = "Create customer objects for existing users that don't have one"

    def handle(self, *args, **options):
        backend = get_backend()      
        backend.init_customers(*args, **options)
