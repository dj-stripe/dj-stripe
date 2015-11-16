from __future__ import unicode_literals
import warnings

__title__ = "dj-stripe"
__summary__ = "Django + Stripe Made Easy"
__uri__ = "https://github.com/pydanny/dj-stripe/"

__version__ = "0.7.0"

__author__ = "Daniel Greenfeld"
__email__ = "pydanny@gmail.com"

__license__ = "BSD"
__license__ = "License :: OSI Approved :: BSD License"
__copyright__ = "Copyright 2015 Daniel Greenfeld"

try:
    from django import get_version as get_django_version

    if get_django_version() <= '1.6.x':
        msg = "dj-stripe deprecation notice: Django 1.6 and lower are no longer\n" \
            "supported. Please upgrade to Django 1.7 or higher.\n" \
            "Reference: https://github.com/pydanny/dj-stripe/issues/173"
        warnings.warn(msg)
except ImportError:
    # during pip installation django might not be present yet
    pass
