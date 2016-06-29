# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from braces.views import CsrfExemptMixin, FormValidMessageMixin, LoginRequiredMixin, SelectRelatedMixin
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponse
from django.http.response import HttpResponseNotFound
from django.shortcuts import render, redirect
from django.utils.encoding import smart_str
from django.views.generic import DetailView, FormView, TemplateView, View
from stripe.error import StripeError

from . import settings as djstripe_settings
from .forms import PlanForm, CancelSubscriptionForm
from .mixins import PaymentsContextMixin, SubscriptionMixin
from .models import Customer, Event, EventProcessingException, Plan
from .sync import sync_subscriber


# ============================================================================ #
#                                 Account Views                                #
# ============================================================================ #
class AccountView(LoginRequiredMixin, SelectRelatedMixin, SubscriptionMixin, PaymentsContextMixin, TemplateView):
    """Shows account details including customer and subscription details."""
    template_name = "djstripe/account.html"


# ============================================================================ #
#                                 Billing Views                                #
# ============================================================================ #

class ChangeCardView(LoginRequiredMixin, PaymentsContextMixin, DetailView):
    """TODO: Needs to be refactored to leverage forms and context data."""
    template_name = "djstripe/change_card.html"

    def get_object(self):
        if hasattr(self, "customer"):
            return self.customer
        self.customer, _created = Customer.get_or_create(
            subscriber=djstripe_settings.subscriber_request_callback(self.request))
        return self.customer

    def post(self, request, *args, **kwargs):
        """
        TODO: Raise a validation error when a stripe token isn't passed.
            Should be resolved when a form is used.
        """

        customer = self.get_object()
        try:
            send_invoice = not customer.default_source
            customer.add_card(
                request.POST.get("stripe_token")
            )
            if send_invoice:
                customer.send_invoice()
            customer.retry_unpaid_invoices()
        except StripeError as exc:
            messages.info(request, "Stripe Error")
            return render(
                request,
                self.template_name,
                {
                    "customer": self.get_object(),
                    "stripe_error": str(exc)
                }
            )
        messages.info(request, "Your card is now updated.")
        return redirect(self.get_post_success_url())

    def get_post_success_url(self):
        """ Makes it easier to do custom dj-stripe integrations. """
        return reverse("djstripe:account")


class HistoryView(LoginRequiredMixin, SelectRelatedMixin, DetailView):
    template_name = "djstripe/history.html"
    model = Customer
    select_related = ["invoice"]

    def get_object(self):
        customer, _created = Customer.get_or_create(
            subscriber=djstripe_settings.subscriber_request_callback(self.request))
        return customer


class SyncHistoryView(CsrfExemptMixin, LoginRequiredMixin, View):
    """TODO: Needs to be refactored to leverage context data."""

    template_name = "djstripe/includes/_history_table.html"

    def post(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            {"customer": sync_subscriber(djstripe_settings.subscriber_request_callback(request))}
        )


# ============================================================================ #
#                              Subscription Views                              #
# ============================================================================ #

class ConfirmFormView(LoginRequiredMixin, FormValidMessageMixin, SubscriptionMixin, FormView):

    form_class = PlanForm
    template_name = "djstripe/confirm_form.html"
    success_url = reverse_lazy("djstripe:history")
    form_valid_message = "You are now subscribed!"

    def get(self, request, *args, **kwargs):
        plan_id = self.kwargs['plan_id']

        if not Plan.objects.filter(id=plan_id).exists():
            return HttpResponseNotFound()

        customer, _created = Customer.get_or_create(subscriber=djstripe_settings.subscriber_request_callback(self.request))

        if customer.subscription and str(customer.subscription.plan.id) == plan_id and customer.subscription.is_valid():
            message = "You already subscribed to this plan"
            messages.info(request, message, fail_silently=True)
            return redirect("djstripe:subscribe")

        return super(ConfirmFormView, self).get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(ConfirmFormView, self).get_context_data(**kwargs)
        context['plan'] = Plan.objects.get(id=self.kwargs['plan_id'])
        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            try:
                customer, _created = Customer.get_or_create(subscriber=djstripe_settings.subscriber_request_callback(self.request))
                customer.add_card(self.request.POST.get("stripe_token"))
                customer.subscribe(form.cleaned_data["plan"])
            except StripeError as exc:
                form.add_error(None, str(exc))
                return self.form_invalid(form)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class SubscribeView(LoginRequiredMixin, SubscriptionMixin, TemplateView):
    template_name = "djstripe/subscribe.html"


class ChangePlanView(LoginRequiredMixin, FormValidMessageMixin, SubscriptionMixin, FormView):
    """
    TODO: Work in a trial_days kwarg

    Also, this should be combined with ConfirmFormView.
    """

    form_class = PlanForm
    template_name = "djstripe/confirm_form.html"
    success_url = reverse_lazy("djstripe:history")
    form_valid_message = "You've just changed your plan!"

    def post(self, request, *args, **kwargs):
        form = PlanForm(request.POST)

        customer, _created = Customer.get_or_create(subscriber=djstripe_settings.subscriber_request_callback(self.request))

        if not customer.subscription:
            form.add_error(None, "You must already be subscribed to a plan before you can change it.")
            return self.form_invalid(form)

        if form.is_valid():
            try:
                selected_plan = form.cleaned_data["plan"]

                # When a customer upgrades their plan, and DJSTRIPE_PRORATION_POLICY_FOR_UPGRADES is set to True,
                # we force the proration of the current plan and use it towards the upgraded plan,
                # no matter what DJSTRIPE_PRORATION_POLICY is set to.
                if djstripe_settings.PRORATION_POLICY_FOR_UPGRADES:
                    # Is it an upgrade?
                    if selected_plan.amount > customer.subscription.plan.amount:
                        customer.subscription.update(plan=selected_plan, prorate=True)
                    else:
                        customer.subscription.update(plan=selected_plan)
                else:
                    customer.subscription.update(plan=selected_plan)
            except StripeError as exc:
                form.add_error(None, str(exc))
                return self.form_invalid(form)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class CancelSubscriptionView(LoginRequiredMixin, SubscriptionMixin, FormView):
    template_name = "djstripe/cancel_subscription.html"
    form_class = CancelSubscriptionForm
    success_url = reverse_lazy("djstripe:account")

    def form_valid(self, form):
        customer, _created = Customer.get_or_create(subscriber=djstripe_settings.subscriber_request_callback(self.request))
        subscription = customer.subscription.cancel()

        if subscription.status == subscription.STATUS_CANCELED:
            # If no pro-rate, they get kicked right out.
            messages.info(self.request, "Your subscription is now cancelled.")
            # logout the user
            auth_logout(self.request)
            return redirect("home")
        else:
            # If pro-rate, they get some time to stay.
            messages.info(self.request, "Your subscription status is now '{status}' until '{period_end}'".format(
                status=subscription.status, period_end=subscription.current_period_end)
            )

        return super(CancelSubscriptionView, self).form_valid(form)


# ============================================================================ #
#                                 Web Services                                 #
# ============================================================================ #


class WebHook(CsrfExemptMixin, View):

    def post(self, request, *args, **kwargs):
        body = smart_str(request.body)
        data = json.loads(body)

        if Event.stripe_objects.exists_by_json(data):
            EventProcessingException.objects.create(
                data=data,
                message="Duplicate event record",
                traceback=""
            )
        else:
            event = Event._create_from_stripe_object(data)
            event.validate()

            if djstripe_settings.WEBHOOK_EVENT_CALLBACK:
                djstripe_settings.WEBHOOK_EVENT_CALLBACK(event)
            else:
                event.process()

        return HttpResponse()
