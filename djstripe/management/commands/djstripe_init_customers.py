from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from djstripe.models import Customer
from djstripe.settings import User


class Command(BaseCommand):

    help = "Create customer objects for existing users that don't have one"

    def handle(self, *args, **options):
        for user in User.objects.filter(customer__isnull=True):
            # use get_or_create in case of race conditions on large
            #      user bases
            Customer.get_or_create(user=user)
            print("Created customer for {0}".format(user.email))
