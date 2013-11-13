from __future__ import unicode_literals
import json

from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
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
from .settings import PY3
from .settings import User
from .sync import sync_customer


class ChangeCardView(LoginRequiredMixin, PaymentsContextMixin, DetailView):
    # TODO - needs tests
    # Needs a form
    # Not done yet
    template_name = "djstripe/change_card.html"

    def get_object(self):
        if hasattr(self, "customer"):
            return self.customer
        self.customer, created = Customer.get_or_create(self.request.user)
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
        return redirect("djstripe:account")


class CancelSubscriptionView(LoginRequiredMixin, PaymentsContextMixin, FormView):
    # TODO - needs tests
    template_name = "djstripe/cancel_subscription.html"
    form_class = CancelSubscriptionForm

    def form_valid(self, form):
        customer, created = Customer.get_or_create(self.request.user)
        # TODO - pass in setting to control at_period_end boolean
        current_subscription = customer.cancel_subscription(at_period_end=True)
        if current_subscription.status == current_subscription.STATUS_CANCELLED:
            messages.info(self.request, "Your account is now cancelled.")
        else:
            messages.info(self.request, "Your account status is now '{a}' until '{b}'".format(
                    a=current_subscription.status, b=current_subscription.current_period_end)
            )

        return redirect("djstripe:account")


class WebHook(CsrfExemptMixin, View):

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


class HistoryView(LoginRequiredMixin, SelectRelatedMixin, DetailView):
    # TODO - needs tests
    template_name = "djstripe/history.html"
    model = Customer
    select_related = ["invoice"]

    def get_object(self):
        customer, created = Customer.get_or_create(self.request.user)
        return customer


class SyncHistoryView(CsrfExemptMixin, LoginRequiredMixin, View):
    # TODO - needs tests
    def post(self, request, *args, **kwargs):
        return render(
            request,
            "djstripe/includes/_history_table.html",
            {"customer": sync_customer(request.user)}
        )


class AccountView(LoginRequiredMixin, SelectRelatedMixin, TemplateView):
    # TODO - needs tests
    template_name = "djstripe/account.html"

    def get_context_data(self, *args, **kwargs):
        context = super(AccountView, self).get_context_data(**kwargs)
        customer, created = Customer.get_or_create(self.request.user)
        context['customer'] = customer
        try:
            context['subscription'] = customer.current_subscription
        except CurrentSubscription.DoesNotExist:
            context['subscription'] = None
        context['plans'] = PLAN_LIST
        return context


################## Subscription views


class SubscribeFormView(
        LoginRequiredMixin,
        FormValidMessageMixin,
        SubscriptionMixin,
        FormView):
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
                customer, created = Customer.get_or_create(self.request.user)
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


class ChangePlanView(LoginRequiredMixin,
                        FormValidMessageMixin,
                        SubscriptionMixin,
                        FormView):

    form_class = PlanForm
    template_name = "djstripe/subscribe_form.html"
    success_url = reverse_lazy("djstripe:history")
    form_valid_message = "You've just changed your plan!"

    def post(self, request, *args, **kwargs):
        form = PlanForm(request.POST)
        customer = request.user.customer
        if form.is_valid():
            try:
                customer.subscribe(form.cleaned_data["plan"])
            except stripe.StripeError as e:
                self.error = e.message
                return self.form_invalid(form)
            except Exception as e:
                raise e
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


######### Web services
class CheckAvailableUserAttributeView(View):

    def get(self, request, *args, **kwargs):
        attr_name = self.kwargs['attr_name']
        not_available = User.objects.filter(
                **{attr_name: request.GET.get("v", "")}
        ).exists()
        return HttpResponse(json.dumps(not not_available))
