# -*- coding: utf-8 -*-
"""
.. module:: dj-stripe.mixins.

   :synopsis: dj-stripe Mixins.

.. moduleauthor:: Daniel Greenfield (@pydanny)

"""

from __future__ import unicode_literals

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

from . import settings as djstripe_settings
from .models import Plan, Customer
from .utils import subscriber_has_active_subscription


class SubscriptionPaymentRequiredMixin(object):
    """
    Check if the subscriber has an active subscription.

    If not, redirect to the subscription page.
    """

    def dispatch(self, request, *args, **kwargs):
        """Redirect user to djstripe:subscribe if account is inactive."""
        if not subscriber_has_active_subscription(djstripe_settings.subscriber_request_callback(request)):
            message = "Your account is inactive. Please renew your subscription"
            messages.info(request, message, fail_silently=True)
            return redirect("djstripe:subscribe")

        return super(SubscriptionPaymentRequiredMixin, self).dispatch(request, *args, **kwargs)


class PaymentsContextMixin(object):
    """Adds plan context to a view."""

    def get_context_data(self, **kwargs):
        """Inject STRIPE_PUBLIC_KEY and plans into context_data."""
        context = super(PaymentsContextMixin, self).get_context_data(**kwargs)
        context.update({
            "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
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
