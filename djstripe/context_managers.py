# -*- coding: utf-8 -*-
"""
.. module:: djstripe.context_managers
   :synopsis: dj-stripe Context Managers

.. moduleauthor:: Bill Huneke (@wahuneke)
.. moduleauthor:: Alex Kavanaugh (@akavanau)

"""

from contextlib import contextmanager


@contextmanager
def stripe_temporary_api_key(temp_key):
    """
    A contextmanager

    Temporarily replace the global api_key used in stripe API calls with the given value.
    The original value is restored as soon as context exits.
    """
    import stripe
    backup_key = stripe.api_key
    stripe.api_key = temp_key
    yield
    stripe.api_key = backup_key


@contextmanager
def stripe_temporary_api_version(temp_version):
    """
    A contextmanager

    Temporarily replace the global api_version used in stripe API calls with the given value.
    The original value is restored as soon as context exits.
    """
    import stripe
    backup_version = stripe.api_version
    stripe.api_version = temp_version
    yield
    stripe.api_version = backup_version
