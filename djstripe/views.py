# -*- coding: utf-8 -*-
"""
.. module:: djstripe.webhooks.

  :synopsis: dj-stripe - Views related to the djstripe app.

.. moduleauthor:: @kavdev, @pydanny, @lskillen, @wahuneke, @dollydagr, @chrissmejia
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import logging

from django.contrib import messages
from django.contrib.auth import logout as auth_logout, REDIRECT_FIELD_NAME
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import smart_str
from django.utils.http import is_safe_url
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, TemplateView, View

from . import settings as djstripe_settings
from .enums import SubscriptionStatus
from .forms import CancelSubscriptionForm
from .mixins import SubscriptionMixin
from .models import Customer, Event, EventProcessingException
from .webhooks import TEST_EVENT_ID

logger = logging.getLogger(__name__)


# ============================================================================ #
#                              Subscription Views                              #
# ============================================================================ #

class SubscribeView(LoginRequiredMixin, SubscriptionMixin, TemplateView):
    """A view to render the subscribe template."""

    template_name = "djstripe/subscribe.html"


class CancelSubscriptionView(LoginRequiredMixin, SubscriptionMixin, FormView):
    """A view used to cancel a Customer's subscription."""

    template_name = "djstripe/cancel_subscription.html"
    form_class = CancelSubscriptionForm
    success_url = reverse_lazy("home")
    redirect_url = reverse_lazy("home")

    # messages
    subscription_cancel_message = "Your subscription is now cancelled."
    subscription_status_message = "Your subscription status is now '{status}' until '{period_end}'"

    def get_redirect_url(self):
        """
        Return the URL to redirect to when canceling is successful.
        Looks in query string for ?next, ensuring it is on the same domain.
        """
        next = self.request.GET.get(REDIRECT_FIELD_NAME)

        # is_safe_url() will ensure we don't redirect to another domain
        if next and is_safe_url(next):
            return next
        else:
            return self.redirect_url

    def form_valid(self, form):
        """Handle canceling the Customer's subscription."""
        customer, _created = Customer.get_or_create(
            subscriber=djstripe_settings.subscriber_request_callback(self.request)
        )

        if not customer.subscription:
            # This will trigger if the customer does not have a subscription,
            # or it is already canceled. Do as if the subscription cancels successfully.
            return self.status_cancel()

        subscription = customer.subscription.cancel()

        if subscription.status == SubscriptionStatus.canceled:
            return self.status_cancel()
        else:
            # If pro-rate, they get some time to stay.
            messages.info(self.request, self.subscription_status_message.format(
                status=subscription.status, period_end=subscription.current_period_end)
            )

        return super(CancelSubscriptionView, self).form_valid(form)

    def status_cancel(self):
        """Triggered when the subscription is immediately canceled (not pro-rated)"""
        # If no pro-rate, they get kicked right out.
        messages.info(self.request, self.subscription_cancel_message)
        # logout the user
        auth_logout(self.request)
        # Redirect to next url
        return redirect(self.get_redirect_url())


# ============================================================================ #
#                                 Web Services                                 #
# ============================================================================ #


@method_decorator(csrf_exempt, name="dispatch")
class WebHook(View):
    """A view used to handle webhooks."""

    def post(self, request, *args, **kwargs):
        """
        Create an Event object based on request data.

        Creates an EventProcessingException if the webhook Event is a duplicate.
        """
        body = smart_str(request.body)
        data = json.loads(body)

        if data['id'] == TEST_EVENT_ID:
            logger.info("Test webhook received: {}".format(data['type']))
            return HttpResponse()

        if Event.stripe_objects.exists_by_json(data):
            EventProcessingException.objects.create(
                data=data,
                message="Duplicate event record",
                traceback=""
            )
        else:
            event = Event._create_from_stripe_object(data, save=False)
            event.validate()

            if djstripe_settings.WEBHOOK_EVENT_CALLBACK:
                djstripe_settings.WEBHOOK_EVENT_CALLBACK(event)
            else:
                event.process()

        return HttpResponse()
