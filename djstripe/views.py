from __future__ import unicode_literals
import json

from django.core.urlresolvers import reverse_lazy
from django.db.models import ObjectDoesNotExist
from django.http import HttpResponse
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import TemplateView
from django.views.generic import View

from braces.views import CsrfExemptMixin
from braces.views import LoginRequiredMixin
from braces.views import SelectRelatedMixin
import stripe

from .forms import PlanForm
from .models import Customer
from .models import Event
from .models import EventProcessingException
from .settings import PLAN_CHOICES
from .settings import PY3
from .viewmixins import PaymentsContextMixin


class SubscribeFormView(
        LoginRequiredMixin,
        PaymentsContextMixin,
        FormView):

    form_class = PlanForm
    template_name = "djstripe/subscribe_form.html"
    success_url = reverse_lazy("history")

    def get_context_data(self, *args, **kwargs):
        context = super(SubscribeFormView, self).get_context_data(**kwargs)
        context['is_plans_plural'] = bool(len(PLAN_CHOICES) > 1)
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
                try:
                    customer = self.request.user.customer
                except ObjectDoesNotExist:
                    customer = Customer.create(self.request.user)
                customer.update_card(self.request.POST.get("stripe_token"))
                customer.subscribe(form.cleaned_data["plan"])
            except stripe.StripeError as e:
                # add form error here
                self.error = e.args[0]
                return self.form_invalid(form)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class HistoryView(LoginRequiredMixin, SelectRelatedMixin, DetailView):
    template_name = "djstripe/history.html"
    model = Customer
    select_related = ["invoice"]

    def get_object(self):
        try:
            return self.request.user.customer
        except Customer.DoesNotExist:
            return Customer.create(self.request.user)


class ChangeCardView(LoginRequiredMixin, PaymentsContextMixin, TemplateView):
    template_name = "djstripe/change_card.html"


class CancelView(LoginRequiredMixin, PaymentsContextMixin, TemplateView):
    template_name = "djstripe/cancel.html"


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

