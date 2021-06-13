"""
dj-stripe mixins
"""
import sys
import traceback

from .models import Customer, Plan
from .settings import djstripe_settings


class PaymentsContextMixin:
    """Adds plan context to a view."""

    def get_context_data(self, **kwargs):
        """Inject STRIPE_PUBLIC_KEY and plans into context_data."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "STRIPE_PUBLIC_KEY": djstripe_settings.STRIPE_PUBLIC_KEY,
                "plans": Plan.objects.all(),
            }
        )
        return context


class SubscriptionMixin(PaymentsContextMixin):
    """Adds customer subscription context to a view."""

    def get_context_data(self, *args, **kwargs):
        """Inject is_plans_plural and customer into context_data."""
        context = super().get_context_data(**kwargs)
        context["is_plans_plural"] = Plan.objects.count() > 1
        context["customer"], _created = Customer.get_or_create(
            subscriber=djstripe_settings.subscriber_request_callback(self.request)
        )
        context["subscription"] = context["customer"].subscription
        return context


class VerbosityAwareOutputMixin:
    """
    A mixin class to provide verbosity aware output functions for management commands.
    """

    def set_verbosity(self, options):
        """Set the verbosity based off the passed in options."""
        self.verbosity = options["verbosity"]

    def output(self, arg):
        """Print if output is not silenced."""
        if self.verbosity > 0:
            print(arg)

    def verbose_output(self, arg):
        """Print only if output is verbose."""
        if self.verbosity > 1:
            print(arg)

    def verbose_traceback(self):
        """Print out a traceback if the output is verbose."""
        if self.verbosity > 1:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
