# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import decimal
import json
import logging

from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import TemplateView
from django.views.generic import View
from django.utils.encoding import smart_str

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
from .settings import PAYMENT_PLANS
from .settings import subscriber_request_callback
from .settings import PRORATION_POLICY_FOR_UPGRADES
from .settings import CANCELLATION_AT_PERIOD_END
from .settings import PLAN_CHANGE_TRIAL_POLICY
from .settings import ONE_TRIAL_PER_CUSTOMER
from .sync import sync_subscriber

logger = logging.getLogger(__name__)

# ============================================================================ #
#                                 Account Views                                #
# ============================================================================ #


class AccountView(LoginRequiredMixin, SelectRelatedMixin, TemplateView):
    """Shows account details including customer and subscription details."""
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


# ============================================================================ #
#                                 Billing Views                                #
# ============================================================================ #

class ChangeCardView(LoginRequiredMixin, PaymentsContextMixin, DetailView):
    """TODO: Needs to be refactored to leverage forms and context data."""
    template_name = "djstripe/change_card.html"

    def get_object(self):
        if hasattr(self, "customer"):
            return self.customer
        self.customer, created = Customer.get_or_create(
            subscriber=subscriber_request_callback(self.request))
        return self.customer

    def post(self, request, *args, **kwargs):
        """
        TODO: Raise a validation error when a stripe token isn't passed.
            Should be resolved when a form is used.
        """

        customer = self.get_object()
        try:
            send_invoice = customer.card_fingerprint == ""
            customer.update_card(
                request.POST.get("stripe_token")
            )
            if send_invoice:
                customer.send_invoice()
            customer.retry_unpaid_invoices()
        except stripe.StripeError as exc:
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
        customer, created = Customer.get_or_create(
            subscriber=subscriber_request_callback(self.request))
        return customer


class SyncHistoryView(CsrfExemptMixin, LoginRequiredMixin, View):
    """TODO: Needs to be refactored to leverage context data."""

    template_name = "djstripe/includes/_history_table.html"

    def post(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            {"customer": sync_subscriber(subscriber_request_callback(request))}
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
        plan_slug = self.kwargs['plan']
        if plan_slug not in PAYMENT_PLANS:
            return redirect("djstripe:subscribe")

        plan = PAYMENT_PLANS[plan_slug]
        customer, created = Customer.get_or_create(
            subscriber=subscriber_request_callback(self.request))

        if hasattr(customer, "current_subscription") and customer.current_subscription.plan == plan['plan'] and customer.current_subscription.status != CurrentSubscription.STATUS_CANCELLED:
            message = "You already subscribed to this plan"
            messages.info(request, message, fail_silently=True)
            return redirect("djstripe:subscribe")

        return super(ConfirmFormView, self).get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(ConfirmFormView, self).get_context_data(**kwargs)
        context['plan'] = PAYMENT_PLANS[self.kwargs['plan']]
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
                customer, created = Customer.get_or_create(
                    subscriber=subscriber_request_callback(self.request))
                customer.update_card(self.request.POST.get("stripe_token"))
                customer.subscribe(form.cleaned_data["plan"])
            except stripe.StripeError as exc:
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
    change_trial_policy = PLAN_CHANGE_TRIAL_POLICY
    one_trial_per_customer = ONE_TRIAL_PER_CUSTOMER

    def post(self, request, *args, **kwargs):
        form = PlanForm(request.POST)
        try:
            customer = subscriber_request_callback(request).customer
        except Customer.DoesNotExist as exc:
            form.add_error(None, "You must already be subscribed to a plan before you can change it.")
            return self.form_invalid(form)

        if form.is_valid():
            try:
                prorate = False
                trial_end_date = None
                trial_days = None
                is_trialing = False
                current_trial_end_date = None
                selected_plan_name = form.cleaned_data["plan"]

                try:
                    current_subscription = customer.current_subscription
                except CurrentSubscription.DoesNotExist:
                    current_subscription = None

                if current_subscription:
                    logger.debug('Changing customer %s plan from %s to %s' % (customer.subscriber.email, current_subscription.plan, selected_plan_name))
                    is_trialing = current_subscription.is_status_trialing()
                    current_trial_end_date = current_subscription.trial_end

                new_plan_trial_end = None
                logger.debug("is_trialing: %s" % is_trialing)
                logger.debug("current_trial_end_date: %s" % current_trial_end_date)

                if is_trialing:
                    if self.change_trial_policy == CurrentSubscription.PLAN_CHANGE_TRIAL_POLICY_NEW:
                        # trial_days will be pulled from plan settings in customer.subscribe()
                        pass
                    elif self.change_trial_policy == CurrentSubscription.PLAN_CHANGE_TRIAL_POLICY_CONTINUE:
                        trial_end_date = current_trial_end_date
                        logger.debug('Carrying over trial from current plan that ends %s' % trial_end_date)
                    elif self.change_trial_policy == CurrentSubscription.PLAN_CHANGE_TRIAL_POLICY_END:
                        logger.debug('Not allowing continuation of trial')
                        trial_days = 0
                        
                elif not is_trialing and current_trial_end_date:
                    # Plan is not trialing but plan has trial_end - that means that the user once had a trial.
                    if self.one_trial_per_customer:
                        logger.debug("Customer already had a trial, preventing another")
                        # TODO: Problem here is that new plan will not have trial_end. So if user changes plans
                        #       again, we won't catch this case. I'd say set previous trial_end on the new plan.
                        #       or we'd have to add a property on the customer that indicates if they ever had a trial.
                        trial_days = 0
                        new_plan_trial_end = current_trial_end_date
                    else:
                        logger.debug("Allowing customer to start new trial")

                # When a customer upgrades their plan, and DJSTRIPE_PRORATION_POLICY_FOR_UPGRADES is set to True,
                # we force the proration of the current plan and use it towards the upgraded plan,
                # no matter what DJSTRIPE_PRORATION_POLICY is set to.
                if PRORATION_POLICY_FOR_UPGRADES and current_subscription:
                    current_subscription_amount = current_subscription.amount
                    selected_plan = [plan for plan in PLAN_LIST if plan["plan"] == selected_plan_name][0]  # TODO: refactor
                    selected_plan_price = selected_plan["price"] / decimal.Decimal("100")

                    # Is it an upgrade? then prorate
                    if selected_plan_price > current_subscription_amount:
                        prorate = True

                customer.subscribe(selected_plan_name, prorate=prorate, trial_end_date=trial_end_date, trial_days=trial_days)
                
                # This doesn't work because it's overwritten when we sync with Stripe
                #if new_plan_trial_end:
                    #customer.current_subscription.trial_end = new_plan_trial_end
                    #customer.current_subscription.save()

            except stripe.StripeError as exc:
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
        customer, created = Customer.get_or_create(
            subscriber=subscriber_request_callback(self.request))
        current_subscription = customer.cancel_subscription(
            at_period_end=CANCELLATION_AT_PERIOD_END)

        if current_subscription.status == current_subscription.STATUS_CANCELLED:
            # If no pro-rate, they get kicked right out.
            messages.info(self.request, "Your subscription is now cancelled.")
            # logout the user
            auth_logout(self.request)
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
            event = Event.create_from_stripe_object(data)
            event.validate()
            event.process()
        return HttpResponse()
