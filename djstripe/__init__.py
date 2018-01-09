"""
.. module:: djstripe.

  :synopsis: dj-stripe - Django + Stripe Made Easy
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import pkg_resources

import stripe

from . import checks  # noqa: Register the checks


__version__ = pkg_resources.require("dj-stripe")[0].version


# Set app info
# https://stripe.com/docs/building-plugins#setappinfo
stripe.set_app_info(
    "dj-stripe",
    version=__version__,
    url="https://github.com/dj-stripe/dj-stripe"
)
