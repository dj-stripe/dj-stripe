"""
sync_plans_from_stripe command.
"""
from django.core.management.base import BaseCommand

from ...models import Plan, Price


class Command(BaseCommand):
    """Sync prices (and plans) from stripe."""

    help = "Sync prices (and plans) from stripe."

    def handle(self, *args, **options):
        for price_data in Price.api_list():
            price = Price.sync_from_stripe_data(price_data)
            self.stdout.write(f"Synchronized price {price.id}")

        for plan_data in Plan.api_list():
            plan = Plan.sync_from_stripe_data(plan_data)
            self.stdout.write(f"Synchronized plan {plan.id}")
