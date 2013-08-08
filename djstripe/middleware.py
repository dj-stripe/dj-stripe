from django.conf import settings
from django.core.urlresolvers import resolve
from django.shortcuts import redirect

DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS = getattr(
    settings,
    "DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS",
    ()
)

from .models import Customer


class SubscriptionPaymentMiddleware(object):
    """
    Rules:
        "(app_name)" means everything from this app is exempt
        "[namespace]" means everything with this name is exempt
        "namespace:name" means this namespaced URL is exempt
        "name" means this URL is exempt

    Example::

        DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS = (
            "(allauth)",  # anything in the django-allauth URLConf
            "[djstripe]",  # Anything in the djstripe app
            "products:detail",  # A ProductDetail view you want shown to non-payers
            "home",  # Site homepage

        )
    """

    # TODO - needs tests

    def process_request(self, request):

        # So we don't have crazy long lines of code
        EXEMPT = DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS

        if request.user.is_authenticated() and not request.user.is_staff:
            match = resolve(request.path)
            if "({0})".format(match.app_name) in EXEMPT:
                return

            if "[{0}]".format(match.namespace) in EXEMPT:
                return

            if "{0}:{1}".format(match.namespace, match.url_name) in EXEMPT:
                return

            if match.url_name in EXEMPT:
                return

            customer, created = Customer.get_or_create(request.user)
            if created:
                return redirect("djstripe:subscribe")

            if not customer.has_active_subscription():
                return redirect("djstripe:subscribe")

