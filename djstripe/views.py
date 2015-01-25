# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import decimal
import json

from django.contrib.auth import logout
from django.contrib import messages
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import TemplateView
from django.views.generic import View

from braces.views import CsrfExemptMixin
from braces.views import FormValidMessageMixin
from braces.views import LoginRequiredMixin
from braces.views import SelectRelatedMixin
import stripe

from .forms import PlanForm, CancelSubscriptionForm
from .mixins import PaymentsContextMixin, SubscriptionMixin
from .models import CurrentSubscription
from .models import Customer
from .models import Event
from .models import EventProcessingException
from .settings import PLAN_LIST
from .settings import CANCELLATION_AT_PERIOD_END
from .settings import subscriber_request_callback
from .settings import PRORATION_POLICY_FOR_UPGRADES
from .settings import PY3
from .sync import sync_subscriber


# ============================================================================ #
#                                 Account Views                                #
# ============================================================================ #


class AccountView(LoginRequiredMixin, SelectRelatedMixin, TemplateView):
    # TODO - needs tests
    template_name = "djstripe/account.html"

    def get_context_data(self, *args, **kwargs):
        context = super(AccountView, self).get_context_data(**kwargs)
        customer, created = Customer.get_or_create(
            subscriber=subscriber_request_callback(self.request))
        context['customer'] = customer
        try:
            context['subscription'] = customer.current_subscription
        except CurrentSubscription.DoesNotExist:
            context['subscription'] = None
        context['plans'] = PLAN_LIST
        return context


class ChangeCardView(LoginRequiredMixin, PaymentsContextMixin, DetailView):
    # TODO - needs tests
    # Needs a form
    # Not done yet
    template_name = "djstripe/change_card.html"

    def get_object(self):
        if hasattr(self, "customer"):
            return self.customer
        self.customer, created = Customer.get_or_create(
            subscriber=subscriber_request_callback(self.request))
        return self.customer

    def post(self, request, *args, **kwargs):
        customer = self.get_object()
        try:
            send_invoice = customer.card_fingerprint == ""
            customer.update_card(
                request.POST.get("stripe_token")
            )
            if send_invoice:
                customer.send_invoice()
            customer.retry_unpaid_invoices()
        except stripe.CardError as e:
            messages.info(request, "Stripe Error")
            return render(
                request,
                self.template_name,
                {
                    "customer": self.get_object(),
                    "stripe_error": e.message
                }
            )
        messages.info(request, "Your card is now updated.")
        return redirect(self.get_post_success_url())

    def get_post_success_url(self):
        """ Makes it easier to do custom dj-stripe integrations. """
        return reverse("djstripe:account")


class HistoryView(LoginRequiredMixin, SelectRelatedMixin, DetailView):
    # TODO - needs tests
    template_name = "djstripe/history.html"
    model = Customer
    select_related = ["invoice"]

    def get_object(self):
        customer, created = Customer.get_or_create(
            subscriber=subscriber_request_callback(self.request))
        return customer


class SyncHistoryView(CsrfExemptMixin, LoginRequiredMixin, View):

    template_name = "djstripe/includes/_history_table.html"

    # TODO - needs tests
    def post(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            {"customer": sync_subscriber(subscriber_request_callback(request))}
        )


# ============================================================================ #
#                              Subscription Views                              #
# ============================================================================ #


class SubscribeFormView(LoginRequiredMixin, FormValidMessageMixin, SubscriptionMixin, FormView):
    # TODO - needs tests

    form_class = PlanForm
    template_name = "djstripe/subscribe_form.html"
    success_url = reverse_lazy("djstripe:history")
    form_valid_message = "You are now subscribed!"

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            try:
                customer, created = Customer.get_or_create(
                    subscriber=subscriber_request_callback(self.request))
                customer.update_card(self.request.POST.get("stripe_token"))
                customer.subscribe(form.cleaned_data["plan"])
            except stripe.StripeError as e:
                # add form error here
                self.error = e.args[0]
                return self.form_invalid(form)
            # redirect to confirmation page
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class ChangePlanView(LoginRequiredMixin, FormValidMessageMixin, SubscriptionMixin, FormView):
    # TODO - needs tests

    form_class = PlanForm
    template_name = "djstripe/subscribe_form.html"
    success_url = reverse_lazy("djstripe:history")
    form_valid_message = "You've just changed your plan!"

    def post(self, request, *args, **kwargs):
        form = PlanForm(request.POST)
        customer = subscriber_request_callback(request).customer
        if form.is_valid():
            try:
                # When a customer upgrades their plan, and PRORATION_POLICY_FOR_UPGRADES is set to True,
                # then we force the proration of his current plan and use it towards the upgraded plan,
                # no matter what PRORATION_POLICY is set to.
                if PRORATION_POLICY_FOR_UPGRADES:
                    current_subscription_amount = customer.current_subscription.amount
                    selected_plan_name = form.cleaned_data["plan"]
                    selected_plan = next(
                        (plan for plan in PLAN_LIST if plan["plan"] == selected_plan_name)
                    )
                    selected_plan_price = selected_plan["price"]

                    if not isinstance(selected_plan["price"], decimal.Decimal):
                        selected_plan_price = selected_plan["price"] / decimal.Decimal("100")

                    # Is it an upgrade?
                    if selected_plan_price > current_subscription_amount:
                        customer.subscribe(selected_plan_name, prorate=True)
                    else:
                        customer.subscribe(selected_plan_name)
                else:
                    customer.subscribe(form.cleaned_data["plan"])
            except stripe.StripeError as e:
                self.error = e.message
                return self.form_invalid(form)
            except Exception as e:
                raise e
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class CancelSubscriptionView(LoginRequiredMixin, SubscriptionMixin, FormView):
    # TODO - needs tests
    template_name = "djstripe/cancel_subscription.html"
    form_class = CancelSubscriptionForm
    success_url = reverse_lazy("djstripe:account")

    def form_valid(self, form):
        customer, created = Customer.get_or_create(
            subscriber=subscriber_request_callback(self.request))
        current_subscription = customer.cancel_subscription(
            at_period_end=CANCELLATION_AT_PERIOD_END)

        if current_subscription.status == current_subscription.STATUS_CANCELLED:
            # If no pro-rate, they get kicked right out.
            messages.info(self.request, "Your subscription is now cancelled.")
            # logout the user
            logout(self.request)
            return redirect("home")
        else:
            # If pro-rate, they get some time to stay.
            messages.info(self.request, "Your subscription status is now '{status}' until '{period_end}'".format(
                status=current_subscription.status, period_end=current_subscription.current_period_end)
            )

        return super(CancelSubscriptionView, self).form_valid(form)


# ============================================================================ #
#                                 Web Services                                 #
# ============================================================================ #


class WebHook(CsrfExemptMixin, View):
    # TODO - needs tests

    def post(self, request, *args, **kwargs):
        if PY3:
            # Handles Python 3 conversion of bytes to str
            body = request.body.decode(encoding="UTF-8")
        else:
            # Handles Python 2
            body = request.body
        data = json.loads(body)
        if Event.objects.filter(stripe_id=data["id"]).exists():
            EventProcessingException.objects.create(
                data=data,
                message="Duplicate event record",
                traceback=""
            )
        else:
            event = Event.objects.create(
                stripe_id=data["id"],
                kind=data["type"],
                livemode=data["livemode"],
                webhook_message=data
            )
            event.validate()
            event.process()
        return HttpResponse()
