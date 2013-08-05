from django.contrib import messages
from django.shortcuts import redirect

from .models import Customer


class PaymentRequiredMixin(object):

    def dispatch(self, request, *args, **kwargs):
        customer, create = Customer.objects.get_or_create(
            user=request.user
        )
        if not customer.has_active_subscription():
            msg = "Your account is inactive. Please renew your subscription"
            messages.info(request, msg, fail_silently=True)
            return redirect("subscriptions:subscribe")

        return super(PaymentRequiredMixin, self).dispatch(
            request, *args, **kwargs)
