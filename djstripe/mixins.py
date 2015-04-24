# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib import messages
from django.shortcuts import redirect

from .models import Customer, CurrentSubscription
from . import settings as app_settings
from .utils import subscriber_has_active_subscription


class SubscriptionPaymentRequiredMixin(object):
    """ Used to check to see if someone paid """
    # TODO - needs tests
    def dispatch(self, request, *args, **kwargs):
        if not subscriber_has_active_subscription(app_settings.subscriber_request_callback(request)):
            msg = "Your account is inactive. Please renew your subscription"
            messages.info(request, msg, fail_silently=True)
            return redirect("djstripe:subscribe")

        return super(SubscriptionPaymentRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class PaymentsContextMixin(object):
    """ Used to check to see if someone paid """
    # TODO - needs tests
    def get_context_data(self, **kwargs):
        context = super(PaymentsContextMixin, self).get_context_data(**kwargs)
        context.update({
            "STRIPE_PUBLIC_KEY": app_settings.STRIPE_PUBLIC_KEY,
            "PLAN_CHOICES": app_settings.PLAN_CHOICES,
            "PLAN_LIST": app_settings.PLAN_LIST,
            "PAYMENT_PLANS": app_settings.PAYMENTS_PLANS
        })
        return context


class SubscriptionMixin(PaymentsContextMixin):
    # TODO - needs tests
    def get_context_data(self, *args, **kwargs):
        context = super(SubscriptionMixin, self).get_context_data(**kwargs)
        context['is_plans_plural'] = bool(len(app_settings.PLAN_CHOICES) > 1)
        context['customer'], created = Customer.get_or_create(
            subscriber=app_settings.subscriber_request_callback(self.request))
        context['CurrentSubscription'] = CurrentSubscription
        return context
