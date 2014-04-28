from __future__ import unicode_literals
from functools import wraps

from django.utils.decorators import available_attrs
from django.shortcuts import redirect

from .utils import user_has_active_subscription


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
