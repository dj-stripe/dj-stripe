# -*- coding: utf-8 -*-
"""
.. module:: djstripe.decorators.

   :synopsis: dj-stripe Decorators.

.. moduleauthor:: @pydanny, and @audreyr

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from functools import wraps

from django.shortcuts import redirect
from django.utils.decorators import available_attrs

from .settings import SUBSCRIPTION_REDIRECT, subscriber_request_callback
from .utils import subscriber_has_active_subscription


def subscriber_passes_pay_test(test_func, plan=None, pay_page=SUBSCRIPTION_REDIRECT):
    """
    Decorator for views that checks the subscriber passes the given test for a "Paid Feature".

    Redirects to `pay_page` if necessary. The test should be a callable
    that takes the subscriber object and returns True if the subscriber passes.
    """
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):
            if test_func(subscriber_request_callback(request), plan):
                return view_func(request, *args, **kwargs)

            return redirect(pay_page)
        return _wrapped_view
    return decorator


def subscription_payment_required(function=None, plan=None, pay_page=SUBSCRIPTION_REDIRECT):
    """
    Decorator for views that require subscription payment.

    Redirects to `pay_page` if necessary.
    """
    actual_decorator = subscriber_passes_pay_test(
        subscriber_has_active_subscription,
        plan=plan,
        pay_page=pay_page,
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
