# -*- coding: utf-8 -*-
"""
.. module:: djstripe.context_managers.

   :synopsis: dj-stripe Context Managers

.. moduleauthor:: Bill Huneke (@wahuneke)
.. moduleauthor:: Alex Kavanaugh (@akavanau)
.. moduleauthor:: Lee Skillen (@lskillen)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

from . import settings as djstripe_settings


@contextmanager
def stripe_temporary_api_version(version, validate=True):
    """
    Temporarily replace the global api_version used in stripe API calls with the given value.

    The original value is restored as soon as context exits.
    """
    old_version = djstripe_settings.get_stripe_api_version()

    try:
        djstripe_settings.set_stripe_api_version(version, validate=validate)
        yield
    finally:
        # Validation is bypassed since we're restoring a previous value.
        djstripe_settings.set_stripe_api_version(old_version, validate=False)
