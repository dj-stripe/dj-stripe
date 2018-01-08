# -*- coding: utf-8 -*-
"""
.. module:: djstripe.webhooks.

  :synopsis: dj-stripe - Views related to the djstripe app.

.. moduleauthor:: @kavdev, @pydanny, @lskillen, @wahuneke, @dollydagr, @chrissmejia
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import is_safe_url
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, TemplateView, View

from . import settings as djstripe_settings
from .enums import SubscriptionStatus
from .forms import CancelSubscriptionForm
from .mixins import SubscriptionMixin
from .models import Customer, WebhookEventTrigger


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
class ProcessWebhookView(View):
    """
    A Stripe Webhook handler view.

    This will create a WebhookEventTrigger instance, verify it,
    then attempt to process it.

    If the webhook cannot be verified, returns HTTP 400.

    If an exception happens during processing, returns HTTP 500.
    """

    def post(self, request):
        if "HTTP_STRIPE_SIGNATURE" not in request.META:
            # Do not even attempt to process/store the event if there is
            # no signature in the headers so we avoid overfilling the db.
            return HttpResponseBadRequest()

        trigger = WebhookEventTrigger.from_request(request)

        if trigger.exception:
            # An exception happened, return 500
            return HttpResponseServerError()

        if trigger.is_test_event:
            # Since we don't do signature verification, we have to skip trigger.valid
            return HttpResponse("Test webhook successfully received!")

        if not trigger.valid:
            # Webhook Event did not validate, return 400
            return HttpResponseBadRequest()

        return HttpResponse(str(trigger.id))
