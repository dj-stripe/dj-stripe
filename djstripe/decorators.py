from __future__ import unicode_literals
from functools import wraps

from django.contrib import messages
from django.utils.decorators import available_attrs
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import redirect

from .models import Customer

ERROR_MSG = (
                "The subscription_payment_required decorator requires the user"
                "be authenticated before use. Please use django.contrib.auth's"
                "login_required decorator."
            )


def user_passes_pay_test(test_func, pay_page="djstripe:subscribe"):
    """
    Decorator for views that checks that the user passes the given test for a "Paid Feature",
    redirecting to the pay form if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)

            return redirect(pay_page)
        return _wrapped_view
    return decorator


def user_has_active_subscription(user):
    """
    Helper function to check if a user has an active subscription.
    Throws improperlyConfigured if user.is_anonymous == True
    """
    if user.is_anonymous():
        raise ImproperlyConfigured
    customer, created = Customer.get_or_create(user)
    if created or not customer.has_active_subscription():
        return False
    return True


def subscription_payment_required(function=None, pay_page="djstripe:subscribe"):
    """
    Decorator for views that require subscription payment, redirecting to the
    subscribe page if necessary.
    """

    actual_decorator = user_passes_pay_test(
        user_has_active_subscription,
        pay_page=pay_page
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
