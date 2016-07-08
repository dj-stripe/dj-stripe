# -*- coding: utf-8 -*-
"""
.. module:: djstripe.exceptions.

   :synopsis: dj-stripe Exceptions.

.. moduleauthor:: @kavdev

"""
from __future__ import unicode_literals


class MultipleSubscriptionException(Exception):
    """Raised when Customer has multiple Subscriptions."""

    pass


class StripeObjectManipulationException(Exception):
    """Raised when Cards are manipulated not through a Customer instance."""

    pass


class CustomerDoesNotExistLocallyException(Exception):
    """Raised when a user tries to create a Customer which does not exist locally."""

    pass
