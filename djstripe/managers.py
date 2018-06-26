# -*- coding: utf-8 -*-
"""
.. module:: djstripe.managers.

   :synopsis: dj-stripe model managers

.. moduleauthor:: @kavdev, @pydanny, @wahuneke
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import decimal

from django.db import models
from six import text_type


class StripeObjectManager(models.Manager):
    """Manager used in StripeObject."""
    pass


class SubscriptionManager(models.Manager):
    """Manager used in models.Subscription."""

    def started_during(self, year, month):
        """Return Subscriptions not in trial status between a certain time range."""
        return self.exclude(status="trialing").filter(start__year=year, start__month=month)

    def active(self):
        """Return active Subscriptions."""
        return self.filter(status="active")

    def canceled(self):
        """Return canceled Subscriptions."""
        return self.filter(status="canceled")

    def canceled_during(self, year, month):
        """Return Subscriptions canceled during a certain time range."""
        return self.canceled().filter(canceled_at__year=year, canceled_at__month=month)

    def started_plan_summary_for(self, year, month):
        """Return started_during Subscriptions with plan counts annotated."""
        return self.started_during(year, month).values("plan").order_by().annotate(count=models.Count("plan"))

    def active_plan_summary(self):
        """Return active Subscriptions with plan counts annotated."""
        return self.active().values("plan").order_by().annotate(count=models.Count("plan"))

    def canceled_plan_summary_for(self, year, month):
        """Return Subscriptions canceled within a time range with plan counts annotated."""
        return self.canceled_during(year, month).values("plan").order_by().annotate(count=models.Count("plan"))

    def churn(self):
        """Return number of canceled Subscriptions divided by active Subscriptions."""
        canceled = self.canceled().count()
        active = self.active().count()
        return decimal.Decimal(text_type(canceled)) / decimal.Decimal(text_type(active))


class TransferManager(models.Manager):
    """Manager used by models.Transfer."""

    def during(self, year, month):
        """Return Transfers between a certain time range."""
        return self.filter(date__year=year, date__month=month)

    def paid_totals_for(self, year, month):
        """Return paid Transfers during a certain year, month with total amounts annotated."""
        return self.during(year, month).filter(status="paid").aggregate(total_amount=models.Sum("amount"))


class ChargeManager(models.Manager):
    """Manager used by models.Charge."""

    def during(self, year, month):
        """Return Charges between a certain time range based on `created`."""
        return self.filter(created__year=year, created__month=month)

    def paid_totals_for(self, year, month):
        """Return paid Charges during a certain year, month with total amount, fee and refunded annotated."""
        return self.during(year, month).filter(paid=True).aggregate(
            total_amount=models.Sum("amount"),
            total_fee=models.Sum("fee"),
            total_refunded=models.Sum("amount_refunded")
        )
