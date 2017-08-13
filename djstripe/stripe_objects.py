# -*- coding: utf-8 -*-

import warnings

from .models import *  # noqa, isort:skip

warnings.warn(
    "djstripe.stripe_objects is a deprecated module, please use djstripe.models",
    DeprecationWarning
)
