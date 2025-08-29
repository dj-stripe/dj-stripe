from django.core.management.base import BaseCommand

from ...utils import clear_expired_idempotency_keys


class Command(BaseCommand):
    help = "Deleted expired Stripe idempotency keys."

    def handle(self, *args, **options):
        clear_expired_idempotency_keys()
