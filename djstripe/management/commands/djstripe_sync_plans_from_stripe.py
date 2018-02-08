# -*- coding: utf-8 -*-
"""
.. module:: djstripe.management.commands.djstriple_sync_plans_from_stripe.

   :synopsis: dj-stripe - sync_plans_from_stripe command.

.. moduleauthor:: @beheh

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.management.base import BaseCommand

from ...models import Plan


class Command(BaseCommand):
    """Sync plans from stripe."""

    help = "Sync plans from stripe."

    def handle(self, *args, **options):
        """Call sync_from_stripe_data for each plan returned by api_list."""
        for plan_data in Plan.api_list():
            plan = Plan.sync_from_stripe_data(plan_data)
            print("Synchronized plan {0}".format(plan.stripe_id))
