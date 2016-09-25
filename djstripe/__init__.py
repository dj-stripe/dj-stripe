from __future__ import unicode_literals
import warnings

from django import VERSION as django_version

__title__ = "dj-stripe"
__summary__ = "Django + Stripe Made Easy"
__uri__ = "https://github.com/kavdev/dj-stripe/"

__version__ = "0.9.0.dev0"

__author__ = "Alexander Kavanaugh"
__email__ = "contact@kavdev.io"

__license__ = "BSD"
__license__ = "License :: OSI Approved :: BSD License"
__copyright__ = "Copyright 2016 Alexander Kavanaugh"

if django_version < (1, 8):
    msg = "dj-stripe deprecation notice: Django 1.7 and lower are no longer\n" \
        "supported. Please upgrade to Django 1.8 or higher.\n" \
        "Reference: https://github.com/kavdev/dj-stripe/issues/275"
    warnings.warn(msg)
