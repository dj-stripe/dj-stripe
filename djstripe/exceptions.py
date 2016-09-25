# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class MultipleSubscriptionException(Exception):
    pass


class StripeObjectManipulationException(Exception):
    pass


class CustomerDoesNotExistLocallyException(Exception):
    pass
