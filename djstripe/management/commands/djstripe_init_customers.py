"""
init_customers command.
"""
from django.core.management.base import BaseCommand

from ...models import Customer
from ...settings import get_subscriber_model


class Command(BaseCommand):
    """Create customer objects for existing subscribers that don't have one."""

    help = "Create customer objects for existing subscribers that don't have one"

    def handle(self, *args, **options):
        """
        Create Customer objects for Subscribers without Customer objects associated.
        """
        for subscriber in get_subscriber_model().objects.filter(
            djstripe_customers=None
        ):
            # use get_or_create in case of race conditions on large subscriber bases
            Customer.get_or_create(subscriber=subscriber)
            print("Created subscriber for {0}".format(subscriber.email))
