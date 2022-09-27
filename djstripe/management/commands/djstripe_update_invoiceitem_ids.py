from django.core.management.base import BaseCommand
from django.db import transaction

from ...models.billing import InvoiceItem

no_results_msg = (
    "There are no more potential InvoiceItems to migrate. "
    "You do not need to run this command anymore."
)


class Command(BaseCommand):
    help = "Update old InvoiceItem IDs to the new, 2019-12-03 format."

    def add_arguments(self, parser):
        """Add optional arguments to filter Events by."""
        # Use a mutually exclusive group to prevent multiple arguments being
        # specified together.
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--i-understand",
            action="store_true",
            help="Run the command, once you've read the warning and understand it.",
        )

    def handle(self, *args, **options):
        invoice_items = InvoiceItem.objects.filter(id__contains="-il_")
        count = invoice_items.count()

        if not options["i_understand"]:
            self.stderr.write(
                "In Stripe API 2019-12-03, the format of invoice line items changed. "
                "This means that existing InvoiceItem objects with the old ID format "
                "may still be in the database and need to be migrated.\n"
                "This is a destructive migration, but this command will attempt to "
                "perform it as safely as possible.\n"
                "More information: https://stripe.com/docs/upgrades#2019-12-03\n\n"
            )
            if count:
                first_few_ids = invoice_items[:10].values_list("id", flat=True)
                self.stdout.write(f"I have found {count} InvoiceItems to migrate:")
                self.stdout.write(
                    "    " + ", ".join(first_few_ids) + f", … (and {count-10} more)"
                    if count > 10
                    else ""
                )
                self.stderr.write(
                    "To perform this migration, run this again with `--i-understand`."
                )
            else:
                self.stdout.write(no_results_msg)
            return

        if not count:
            self.stdout.write(no_results_msg)
            return

        for ii in invoice_items:
            old_id = ii.id
            new_id = old_id.partition("-")[2]
            if "-" in new_id or not new_id.startswith("il_"):
                self.stderr.write(
                    f"Don't know how to migrate {old_id!r}. This is a bug. "
                    "Could you report it?\n https://github.com/dj-stripe/dj-stripe"
                )
                continue

            self.stdout.write(f"Migrating {old_id} => {new_id}")
            with transaction.atomic():
                ii.id = new_id
                stripe_data = ii.api_retrieve()
                ii.save()
                InvoiceItem.sync_from_stripe_data(stripe_data)
