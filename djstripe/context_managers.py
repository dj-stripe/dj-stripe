# -*- coding: utf-8 -*-
"""
.. module:: djstripe.context_managers.

   :synopsis: dj-stripe Context Managers

.. moduleauthor:: Bill Huneke (@wahuneke)
.. moduleauthor:: Alex Kavanaugh (@akavanau)

"""

from contextlib import contextmanager


@contextmanager
def stripe_temporary_api_version(temp_version):
    """
    Temporarily replace the global api_version used in stripe API calls with the given value.

    The original value is restored as soon as context exits.
    """
    import stripe
    backup_version = stripe.api_version
    stripe.api_version = temp_version
    yield
    stripe.api_version = backup_version
