# -*- coding: utf-8 -*-
"""
.. module:: djstripe.management.commands.djstripe_init_plans.

   :synopsis: dj-stripe - init_plans command.

.. moduleauthor:: @kavdev, @pydanny

"""
from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from ...sync import sync_plans


class Command(BaseCommand):
    """Make sure your Stripe account has the plans."""

    help = "Make sure your Stripe account has the plans"

    def handle(self, *args, **options):
        """Call sync_plans."""
        sync_plans()
