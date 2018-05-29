"""
.. module:: djstripe.

  :synopsis: dj-stripe - Django + Stripe Made Easy
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import pkg_resources

from django.apps import AppConfig


__version__ = pkg_resources.require("dj-stripe")[0].version

default_app_config = "djstripe.DjstripeAppConfig"


class DjstripeAppConfig(AppConfig):
    """
    An AppConfig for dj-stripe which loads system checks
    and event handlers once Django is ready.
    """

    name = "djstripe"

    def ready(self):
        import stripe
        from . import checks, event_handlers  # noqa: Register the checks and event handlers

        # Set app info
        # https://stripe.com/docs/building-plugins#setappinfo
        stripe.set_app_info(
            "dj-stripe",
            version=__version__,
            url="https://github.com/dj-stripe/dj-stripe"
        )
