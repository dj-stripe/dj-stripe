from django.core.management.base import BaseCommand

from ... import models
from ...mixins import VerbosityAwareOutputMixin
from ...settings import djstripe_settings


class Command(VerbosityAwareOutputMixin, BaseCommand):
    """Command to process all Events.

    Optional arguments are provided to limit the number of Events processed.

    Note: this is only guaranteed go back at most 30 days based on the
    current limitation of stripe's events API. See: https://stripe.com/docs/api/events
    """

    help = (
        "Process all Events. Use optional arguments to limit the Events to process. "
        "Note: this is only guaranteed go back at most 30 days based on the current "
        "limitation of stripe's events API. See:  https://stripe.com/docs/api/events"
    )

    def add_arguments(self, parser):
        """Add optional arguments to filter Events by."""
        # Use a mutually exclusive group to prevent multiple arguments being
        # specified together.
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--ids",
            nargs="*",
            help="An optional space separated list of specific Event IDs to sync.",
        )
        group.add_argument(
            "--failed",
            action="store_true",
            help="Syncs and processes only the events that have failed webhooks.",
        )
        group.add_argument(
            "--type",
            help=(
                "A string containing a specific event name,"
                " or group of events using * as a wildcard."
                " The list will be filtered to include only"
                " events with a matching event property."
            ),
        )

    def handle(self, *args, **options):
        """Try to process Events listed from the API."""
        # Set the verbosity to determine how much we output, if at all.
        self.set_verbosity(options)

        event_ids = options["ids"]
        failed = options["failed"]
        type_filter = options["type"]

        # Args are mutually exclusive,
        # so output what we are doing based on that assumption.
        if failed:
            self.output("Processing all failed events")
        elif type_filter:
            self.output(
                "Processing all events that match {filter}".format(filter=type_filter)
            )
        elif event_ids:
            self.output("Processing specific events {events}".format(events=event_ids))
        else:
            self.output("Processing all available events")

        # Either use the specific event IDs to retrieve data, or use the api_list
        # if no specific event IDs are specified.
        if event_ids:
            listed_events = (
                models.Event.stripe_class.retrieve(
                    id=event_id, api_key=djstripe_settings.STRIPE_SECRET_KEY
                )
                for event_id in event_ids
            )
        else:
            list_kwargs = {}
            if failed:
                list_kwargs["delivery_success"] = False

            if type_filter:
                list_kwargs["type"] = type_filter

            listed_events = models.Event.api_list(**list_kwargs)

        self.process_events(listed_events)

    def process_events(self, listed_events):
        # Process each listed event. Capture failures and continue,
        # outputting debug information as verbosity dictates.
        count = 0
        total = 0
        for event_data in listed_events:
            try:
                total += 1
                event = models.Event.process(data=event_data)
                count += 1
                self.verbose_output(f"\tSynced Event {event.id}")
            except Exception as exception:
                self.verbose_output(f"\tFailed processing Event {event_data['id']}")
                self.output(f"\t{exception}")
                self.verbose_traceback()

        if total == 0:
            self.output("\t(no results)")
        else:
            self.output(f"\tProcessed {count} out of {total} Events")
