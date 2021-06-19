import stripe
from django.db import models

from .. import enums
from ..fields import JSONField, StripeDateTimeField, StripeEnumField, StripeForeignKey
from .base import StripeModel


# TODO Add Tests
class ScheduledQueryRun(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/api#scheduled_queries
    """

    stripe_class = stripe.sigma.ScheduledQueryRun

    data_load_time = StripeDateTimeField(
        help_text="When the query was run, Sigma contained a snapshot of your "
        "Stripe data at this time."
    )
    error = JSONField(
        null=True,
        blank=True,
        help_text="If the query run was not succeesful, contains information "
        "about the failure.",
    )
    file = StripeForeignKey(
        "file",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The file object representing the results of the query.",
    )
    result_available_until = StripeDateTimeField(
        help_text="Time at which the result expires and is no longer available "
        "for download."
    )
    sql = models.TextField(max_length=5000, help_text="SQL for the query.")
    status = StripeEnumField(
        enum=enums.ScheduledQueryRunStatus, help_text="The query's execution status."
    )
    title = models.TextField(max_length=5000, help_text="Title of the query.")

    # TODO Write corresponding test
    def __str__(self):
        return f"{self.title or self.id} ({self.status})"
