"""
.. module:: djstripe.

  :synopsis: dj-stripe - Django + Stripe Made Easy
"""
from __future__ import unicode_literals
import pkg_resources

from django import VERSION as django_version


__version__ = pkg_resources.require("dj-stripe")[0].version


if django_version < (1, 8):
    import warnings
    msg = "dj-stripe deprecation notice: Django 1.7 and lower are no longer\n" \
        "supported. Please upgrade to Django 1.8 or higher.\n" \
        "Reference: https://github.com/kavdev/dj-stripe/issues/275"
    warnings.warn(msg)
