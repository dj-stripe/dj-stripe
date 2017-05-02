# -*- coding: utf-8 -*-
"""
.. module:: djstripe.checks.

   :synopsis: dj-stripe System Checks

.. moduleauthor:: Alex Kavanaugh (@akavanau)
.. moduleauthor:: Jerome Leclanche (@jleclanche)
.. moduleauthor:: Lee Skillen (@lskillen)

"""
from __future__ import unicode_literals

from django.core import checks
from django.utils import six
from django.core.exceptions import ImproperlyConfigured


@checks.register("djstripe")
def check_stripe_api_key(app_configs=None, **kwargs):
    """Check the user has configured API live/test keys correctly."""
    from . import settings as djstripe_settings
    messages = []

    if not djstripe_settings.STRIPE_SECRET_KEY:
        msg = "Could not find a Stripe API key."
        hint = "Add STRIPE_TEST_SECRET_KEY and STRIPE_LIVE_SECRET_KEY to your settings."
        messages.append(checks.Critical(msg, hint=hint, id="djstripe.C001"))
    elif djstripe_settings.STRIPE_LIVE_MODE:
        if not djstripe_settings.LIVE_API_KEY.startswith("sk_live_"):
            msg = "Bad Stripe live API key."
            hint = 'STRIPE_LIVE_SECRET_KEY should start with "sk_live_"'
            messages.append(checks.Critical(msg, hint=hint, id="djstripe.C002"))
    else:
        if not djstripe_settings.TEST_API_KEY.startswith("sk_test_"):
            msg = "Bad Stripe test API key."
            hint = 'STRIPE_TEST_SECRET_KEY should start with "sk_test_"'
            messages.append(checks.Critical(msg, hint=hint, id="djstripe.C003"))

    return messages


@checks.register("djstripe")
def check_stripe_api_version(app_configs=None, **kwargs):
    """Check the user has configured API version correctly."""
    from . import settings as djstripe_settings
    messages = []
    default_version = djstripe_settings.DEFAULT_STRIPE_API_VERSION
    version = djstripe_settings.get_stripe_api_version()

    try:
        djstripe_settings.check_stripe_api_version(version)
    except ImproperlyConfigured as ex:
        hint = "Use a valid date string value."
        messages.append(checks.Critical(six.force_text(ex), hint=hint, id="djstripe.C004"))

    if version != default_version:
        msg = (
            "The Stripe API version has a non-default value of '{}'. "
            "Non-default versions are not explicitly supported, and may "
            "cause compatibility issues.".format(version)
        )
        hint = "Use the dj-stripe default for Stripe API version: {}".format(default_version)
        messages.append(checks.Warning(msg, hint=hint, id="djstripe.W001"))

    return messages
