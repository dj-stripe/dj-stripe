# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import resolve
from django.shortcuts import redirect
from .models import Customer

DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS = getattr(
    settings,
    "DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS",
    ()
)

DJSTRIPE_SUBSCRIPTION_REDIRECT = getattr(
    settings,
    "DJSTRIPE_SUBSCRIPTION_REDIRECT",
    "djstripe:subscribe"
)

# So we don't have crazy long lines of code
EXEMPT = list(DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS)
EXEMPT.append("[djstripe]")


class SubscriptionPaymentMiddleware(object):
    """
    Rules:

        * "(app_name)" means everything from this app is exempt
        * "[namespace]" means everything with this name is exempt
        * "namespace:name" means this namespaced URL is exempt
        * "name" means this URL is exempt
        * The entire djtripe namespace is exempt
        * If settings.DEBUG is True, then django-debug-toolbar is exempt

    Example::

        DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS = (
            "(allauth)",  # anything in the django-allauth URLConf
            "[blogs]",  # Anything in the blogs namespace
            "products:detail",  # A ProductDetail view you want shown to non-payers
            "home",  # Site homepage
        )
    """

    # TODO - needs tests

    def process_request(self, request):

        if request.user.is_authenticated() and not request.user.is_staff:
            # First, if in DEBUG mode and with django-debug-toolbar, we skip
            #   this entire process.
            if settings.DEBUG and request.path.startswith("/__debug__"):
                return

            # Second we check against matches
            match = resolve(request.path)
            if "({0})".format(match.app_name) in EXEMPT:
                return

            if "[{0}]".format(match.namespace) in EXEMPT:
                return

            if "{0}:{1}".format(match.namespace, match.url_name) in EXEMPT:
                return

            if match.url_name in EXEMPT:
                return

            # TODO: Consider converting to use
            #       djstripe.utils.user_has_active_subscription function
            customer, created = Customer.get_or_create(request.user)
            if created:
                return redirect(DJSTRIPE_SUBSCRIPTION_REDIRECT)

            if not customer.has_active_subscription():
                return redirect(DJSTRIPE_SUBSCRIPTION_REDIRECT)

        # TODO get this working in tests
        # if request.user.is_anonymous():
        #     raise ImproperlyConfigured
