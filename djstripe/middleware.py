# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.urlresolvers import resolve
from django.shortcuts import redirect

import fnmatch

from .utils import subscriber_has_active_subscription
from .settings import subscriber_request_callback


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
        * The entire djstripe namespace is exempt
        * If settings.DEBUG is True, then django-debug-toolbar is exempt
        * A 'fn:' prefix means the rest of the URL is fnmatch'd.

    Example::

        DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS = (
            "[blogs]",  # Anything in the blogs namespace
            "products:detail",  # A ProductDetail view you want shown to non-payers
            "home",  # Site homepage
            "fn:/accounts*",  # anything in the accounts/ URL path
        )
    """

    def process_request(self, request):

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

        # Third, we check wildcards:
        for exempt in [x for x in EXEMPT if x.startswith('fn:')]:
            exempt = exempt.replace('fn:', '')
            if fnmatch.fnmatch(request.path, exempt):
                return

        # Finally, we check the subscriber's subscription status
        subscriber = subscriber_request_callback(request)

        if not subscriber_has_active_subscription(subscriber):
            return redirect(DJSTRIPE_SUBSCRIPTION_REDIRECT)
