from __future__ import unicode_literals
from functools import wraps

from django.contrib import messages
from django.coreexceptions import ImproperlyConfigured
from django.shortcuts import redirect

from .models import Customer

ERROR_MSG = (
                "The subscription_payment_required decorator requires the user"
                "be authenticated before use. Please use django.contrib.auth's"
                "login_required decorator."
            )


def subscription_payment_required(view_func):
    """ Must be called after authentication check is done """
    # TODO - needs tests

    def decorator(request, *args, **kwargs):
        if request.user.is_anonymous():

            raise ImproperlyConfigured("ERROR_MSG")

        # Check to see if user has paid
        customer, created = Customer.get_or_create(request.user)
        if created or not customer.has_active_subscription():
            msg = "Your account is inactive. Please renew your subscription"
            messages.info(request, msg, fail_silently=True)
            return redirect("djstripe:subscribe")

        # wrap and generate response
        response = view_func(request, *args, **kwargs)
        return wraps(response)(decorator)

