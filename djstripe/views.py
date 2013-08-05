from django.core.urlresolvers import reverse_lazy
from django.db.models import ObjectDoesNotExist
from django.views.generic import FormView
from django.views.generic import TemplateView

from braces.views import LoginRequiredMixin
import stripe

from .forms import PlanForm
from .models import Customer
from .settings import PLAN_CHOICES
from .viewmixins import PaymentsContextMixin


class SubscribeFormView(
        LoginRequiredMixin,
        PaymentsContextMixin,
        FormView):

    form_class = PlanForm
    template_name = "djstripe/subscribe.html"
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


class HistoryView(LoginRequiredMixin, TemplateView):
    template_name = "djstripe/history.html"


class ChangeCardView(LoginRequiredMixin, PaymentsContextMixin, TemplateView):
    template_name = "djstripe/change_card.html"


class CancelView(LoginRequiredMixin, PaymentsContextMixin, TemplateView):
    template_name = "djstripe/cancel.html"

