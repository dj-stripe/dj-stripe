# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import decimal

from django.db import models


class StripeObjectManager(models.Manager):

    def exists_by_json(self, data):
        """
        Search for a matching stripe object based on a Stripe object
        received from Stripe in JSON format

        :param data: Stripe event object parsed from a JSON string into an object
        :type data: dict
        :rtype: bool
        :returns: True if the requested object exists, False otherwise
        """
        return self.filter(stripe_id=data["id"]).exists()

    def get_by_json(self, data, field_name="id"):
        """
        Retreive a matching stripe object based on a Stripe object
        received from Stripe in JSON format
        :param data: Stripe event object parsed from a JSON string into an object
        :type data: dict
        """
        return self.get(stripe_id=data[field_name])


class SubscriptionManager(models.Manager):

    def started_during(self, year, month):
        return self.exclude(status="trialing").filter(start__year=year, start__month=month)

    def active(self):
        return self.filter(status="active")

    def canceled(self):
        return self.filter(status="canceled")

    def canceled_during(self, year, month):
        return self.canceled().filter(canceled_at__year=year, canceled_at__month=month)

    def started_plan_summary_for(self, year, month):
        return self.started_during(year, month).values("plan").order_by().annotate(count=models.Count("plan"))

    def active_plan_summary(self):
        return self.active().values("plan").order_by().annotate(count=models.Count("plan"))

    def canceled_plan_summary_for(self, year, month):
        return self.canceled_during(year, month).values("plan").order_by().annotate(count=models.Count("plan"))

    def churn(self):
        canceled = self.canceled().count()
        active = self.active().count()
        return decimal.Decimal(str(canceled)) / decimal.Decimal(str(active))


class TransferManager(models.Manager):

    def during(self, year, month):
        return self.filter(date__year=year, date__month=month)

    def paid_totals_for(self, year, month):
        return self.during(year, month).filter(status="paid").aggregate(total_amount=models.Sum("amount"))


class ChargeManager(models.Manager):

    def during(self, year, month):
        return self.filter(stripe_timestamp__year=year, stripe_timestamp__month=month)

    def paid_totals_for(self, year, month):
        return self.during(year, month).filter(paid=True).aggregate(
            total_amount=models.Sum("amount"),
            total_fee=models.Sum("fee"),
            total_refunded=models.Sum("amount_refunded")
        )
