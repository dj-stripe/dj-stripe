# -*- coding: utf-8 -*-
"""
.. module:: dj-stripe.mixins.

   :synopsis: dj-stripe Mixins.

.. moduleauthor:: Daniel Greenfield (@pydanny)

"""

from __future__ import absolute_import, division, print_function, unicode_literals

from . import settings as djstripe_settings
from .models import Customer, Plan


class PaymentsContextMixin(object):
    """Adds plan context to a view."""

    def get_context_data(self, **kwargs):
        """Inject STRIPE_PUBLIC_KEY and plans into context_data."""
        context = super(PaymentsContextMixin, self).get_context_data(**kwargs)
        context.update({
            "STRIPE_PUBLIC_KEY": djstripe_settings.STRIPE_PUBLIC_KEY,
            "plans": Plan.objects.all(),
        })
        return context


class SubscriptionMixin(PaymentsContextMixin):
    """Adds customer subscription context to a view."""

    def get_context_data(self, *args, **kwargs):
        """Inject is_plans_plural and customer into context_data."""
        context = super(SubscriptionMixin, self).get_context_data(**kwargs)
        context['is_plans_plural'] = Plan.objects.count() > 1
        context['customer'], _created = Customer.get_or_create(
            subscriber=djstripe_settings.subscriber_request_callback(self.request))
        context['subscription'] = context['customer'].subscription
        return context
