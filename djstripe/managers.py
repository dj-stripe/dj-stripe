"""
dj-stripe model managers
"""

import decimal
from datetime import datetime, timedelta, UTC

from django.db import models
from django.db.models.functions import Cast
from django.utils import timezone


def _month_unix_range(year, month):
    """Return (start, end) Unix timestamps spanning the given month."""
    start = datetime(year, month, 1, tzinfo=UTC)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        end = datetime(year, month + 1, 1, tzinfo=UTC)
    return int(start.timestamp()), int(end.timestamp())


class StripeModelManager(models.Manager):
    """Manager used in StripeModel."""

    pass


class SubscriptionManager(models.Manager):
    """Manager used in models.Subscription.

    Most Subscription fields are read from ``stripe_data`` (a JSONField) since
    the dj-stripe 2.10 refactor removed them as concrete columns. ORM filters
    must therefore use ``stripe_data__<key>`` lookups. Date-like fields
    (``start_date``, ``canceled_at``, ``trial_end``) are stored as Unix
    timestamps in the JSON, so range filters are expressed against integer
    bounds.
    """

    def started_during(self, year, month):
        """Return Subscriptions not in trial status between a certain time range."""
        start, end = _month_unix_range(year, month)
        return self.exclude(stripe_data__status="trialing").filter(
            stripe_data__start_date__gte=start,
            stripe_data__start_date__lt=end,
        )

    def active(self):
        """Return active Subscriptions."""
        return self.filter(stripe_data__status="active")

    def canceled(self):
        """Return canceled Subscriptions."""
        return self.filter(stripe_data__status="canceled")

    def canceled_during(self, year, month):
        """Return Subscriptions canceled during a certain time range."""
        start, end = _month_unix_range(year, month)
        return self.canceled().filter(
            stripe_data__canceled_at__gte=start,
            stripe_data__canceled_at__lt=end,
        )

    def started_plan_summary_for(self, year, month):
        """Return started_during Subscriptions with plan counts annotated."""
        return (
            self.started_during(year, month)
            .values("stripe_data__plan__id")
            .order_by()
            .annotate(count=models.Count("stripe_data__plan__id"))
        )

    def active_plan_summary(self):
        """Return active Subscriptions with plan counts annotated."""
        return (
            self.active()
            .values("stripe_data__plan__id")
            .order_by()
            .annotate(count=models.Count("stripe_data__plan__id"))
        )

    def canceled_plan_summary_for(self, year, month):
        """
        Return Subscriptions canceled within a time range with plan counts annotated.
        """
        return (
            self.canceled_during(year, month)
            .values("stripe_data__plan__id")
            .order_by()
            .annotate(count=models.Count("stripe_data__plan__id"))
        )

    def churn(self):
        canceled = self.canceled().count()
        active = self.active().count()
        if active == 0:
            return decimal.Decimal(0)
        return decimal.Decimal(str(canceled)) / decimal.Decimal(str(active))

    def trialing(self):
        return self.filter(stripe_data__status="trialing")

    def expiring_trials(self, days=7):
        now = timezone.now()
        cutoff_date = now + timedelta(days=days)
        return self.trialing().filter(
            stripe_data__trial_end__lte=int(cutoff_date.timestamp()),
            stripe_data__trial_end__gte=int(now.timestamp()),
        )

    def past_due(self):
        return self.filter(stripe_data__status="past_due")

    def incomplete(self):
        return self.filter(stripe_data__status="incomplete")


class TransferManager(models.Manager):
    """Manager used by models.Transfer.

    Transfer-level fields (``status``, ``amount``, ``failure_code``) live in
    ``stripe_data`` as of dj-stripe 2.10.
    """

    def during(self, year, month):
        """Return Transfers between a certain time range."""
        return self.filter(created__year=year, created__month=month)

    def paid_totals_for(self, year, month):
        return self.during(year, month).aggregate(
            total_amount=models.Sum(
                Cast("stripe_data__amount", models.BigIntegerField())
            )
        )

    def failed(self):
        return self.filter(stripe_data__failure_code__isnull=False)

    def pending(self):
        return self.filter(stripe_data__status="pending")


class ChargeManager(models.Manager):
    """Manager used by models.Charge.

    ``status`` is still a concrete column on Charge, but ``paid``,
    ``refunded``, ``disputed``, and ``amount_refunded`` were moved to
    ``stripe_data`` in dj-stripe 2.10 and require JSON lookups.
    """

    def during(self, year, month):
        """Return Charges between a certain time range based on `created`."""
        return self.filter(created__year=year, created__month=month)

    def paid_totals_for(self, year, month):
        return (
            self.during(year, month)
            .filter(stripe_data__paid=True)
            .aggregate(
                total_amount=models.Sum("amount"),
                total_refunded=models.Sum(
                    Cast("stripe_data__amount_refunded", models.BigIntegerField())
                ),
            )
        )

    def succeeded(self):
        return self.filter(status="succeeded")

    def failed(self):
        return self.filter(status="failed")

    def refunded(self):
        return self.filter(stripe_data__refunded=True)

    def disputed(self):
        return self.filter(stripe_data__disputed=True)
