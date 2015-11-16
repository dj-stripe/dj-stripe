# -*- coding: utf-8 -*-
"""
.. module:: dj-stripe.mixins
   :synopsis: dj-stripe Mixins.

.. moduleauthor:: Daniel Greenfield (@pydanny)

"""

from __future__ import unicode_literals

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

from . import settings as djstripe_settings
from .models import Customer, CurrentSubscription
from .utils import subscriber_has_active_subscription


class SubscriptionPaymentRequiredMixin(object):
    """
    Checks if the subscriber has an active subscription. If not, redirect to
    the subscription page.
    """

    def dispatch(self, request, *args, **kwargs):
        if not subscriber_has_active_subscription(djstripe_settings.subscriber_request_callback(request)):
            message = "Your account is inactive. Please renew your subscription"
            messages.info(request, message, fail_silently=True)
            return redirect("djstripe:subscribe")

        return super(SubscriptionPaymentRequiredMixin, self).dispatch(request, *args, **kwargs)


class PaymentsContextMixin(object):
    """Adds plan context to a view."""

    def get_context_data(self, **kwargs):
        context = super(PaymentsContextMixin, self).get_context_data(**kwargs)
        selected_tag = context.get('selected_tag', False)
        if selected_tag:
            plan_list = [x for x in djstripe_settings.PLAN_LIST if x['tag'] == selected_tag]
        else:
            plan_list = djstripe_settings.PLAN_LIST

        context.update({
            "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
            "PLAN_CHOICES": djstripe_settings.PLAN_CHOICES,
            "PLAN_LIST": plan_list,
            "PAYMENT_PLANS": djstripe_settings.PAYMENTS_PLANS,
            "PLAN_TAGS": djstripe_settings.DJSTRIPE_PLANS_TAGS,
            "PLAN_TAGS_DEFAULT": djstripe_settings.DJSTRIPE_PLANS_TAGS_DEFAULT,
            "SELECTED_TAG": selected_tag,
        })
        return context


class SubscriptionMixin(PaymentsContextMixin):
    """Adds customer subscription context to a view."""

    def get_context_data(self, *args, **kwargs):
        context = super(SubscriptionMixin, self).get_context_data(**kwargs)
        context['is_plans_plural'] = bool(len(djstripe_settings.PLAN_CHOICES) > 1)
        context['customer'], created = Customer.get_or_create(
            subscriber=djstripe_settings.subscriber_request_callback(self.request))
        context['CurrentSubscription'] = CurrentSubscription
        return context
