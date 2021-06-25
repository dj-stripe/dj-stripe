"""
init_customers command.
"""
from django.core.management.base import BaseCommand

from ...models import Customer
from ...settings import djstripe_settings


class Command(BaseCommand):
    """Create customer objects for existing subscribers that don't have one."""

    help = "Create customer objects for existing subscribers that don't have one"

    def handle(self, *args, **options):
        """
        Create Customer objects for Subscribers without Customer objects associated.
        """
        subscriber_qs = djstripe_settings.get_subscriber_model().objects.filter(
            djstripe_customers=None
        )
        if subscriber_qs:
            for subscriber in subscriber_qs:
                # use get_or_create in case of race conditions on large subscriber bases
                Customer.get_or_create(subscriber=subscriber)
                self.stdout.write(f"Created subscriber for {subscriber.email}")
        else:
            self.stdout.write("All Customers already have subscribers")
