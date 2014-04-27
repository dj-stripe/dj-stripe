from __future__ import unicode_literals
from django.contrib import messages
from django.shortcuts import redirect

from .models import Customer, CurrentSubscription
from . import settings as app_settings
from .utils import related_model_has_active_subscription
from .backends import get_backend

ERROR_MSG = (
                "SubscriptionPaymentRequiredMixin requires the user be"
                "authenticated before use. Please use django-braces'"
                "LoginRequiredMixin."
            )


class SubscriptionPaymentRequiredMixin(object):
    """ Used to check to see if someone paid """
    # TODO - needs tests
    def dispatch(self, request, *args, **kwargs):
        if not related_model_has_active_subscription(backend.get_related_model(request)):
            msg = "Your account is inactive. Please renew your subscription"
            messages.info(request, msg, fail_silently=True)
            return redirect("djstripe:subscribe")

        return super(SubscriptionPaymentRequiredMixin, self).dispatch(
            request, *args, **kwargs)


class PaymentsContextMixin(object):
    """ Used to check to see if someone paid """
    def get_context_data(self, **kwargs):
        context = super(PaymentsContextMixin, self).get_context_data(**kwargs)
        context.update({
            "STRIPE_PUBLIC_KEY": app_settings.STRIPE_PUBLIC_KEY,
            "PLAN_CHOICES": app_settings.PLAN_CHOICES,
            "PAYMENT_PLANS": app_settings.PAYMENTS_PLANS
        })
        return context


class SubscriptionMixin(PaymentsContextMixin):
    def get_context_data(self, *args, **kwargs):
        context = super(SubscriptionMixin, self).get_context_data(**kwargs)
        context['is_plans_plural'] = bool(len(app_settings.PLAN_CHOICES) > 1)
        backend = get_backend()      
        context['customer'], created = backend.create_customer(self.request)        
        context['CurrentSubscription'] = CurrentSubscription
        return context
