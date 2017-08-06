# -*- coding: utf-8 -*-
"""
.. module:: djstripe.exceptions.

   :synopsis: dj-stripe Exceptions.

.. moduleauthor:: @kavdev

"""
from __future__ import absolute_import, division, print_function, unicode_literals


class MultipleSubscriptionException(Exception):
    """Raised when a Customer has multiple Subscriptions and only one is expected."""

    pass


class StripeObjectManipulationException(Exception):
    """Raised when an attempt to manipulate a non-standalone stripe object is made not through its parent object."""

    pass
