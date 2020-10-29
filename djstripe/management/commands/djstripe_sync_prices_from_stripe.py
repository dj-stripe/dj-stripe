"""
sync_prices_from_stripe command.
"""
from django.core.management.base import BaseCommand

from ...models import Price


class Command(BaseCommand):
    """Sync prices from stripe."""

    help = "Sync prices from stripe."

    def handle(self, *args, **options):
        """Call sync_from_stripe_data for each plan returned by api_list."""
        for price_data in Price.api_list():
            price = Price.sync_from_stripe_data(price_data)
            print("Synchronized plan {0}".format(price.id))
