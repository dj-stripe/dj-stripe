# -*- coding: utf-8 -*-
"""
.. module:: djstripe.webhooks
   :synopsis: dj-stripe - Utils related to processing or registering for webhooks

.. moduleauthor:: Bill Huneke (@wahuneke)

A model registers itself here if it wants to be in the list of processing
functions for a particular webhook. Each processor will have the ability
to modify the event object, access event data, and do what it needs to do

registrations are keyed by top-level event type (e.g. "invoice", "customer", etc)
Each registration entry is a list of processors
Each processor in these lists is a function to be called
The function signature is:
     <Event object> <event data dict> <event type> <event sub type>

The <event data dict> parameter should be a dict() structure, as received from Stripe
on webhook. This dict contains an 'object' member and also, sometimes, a 'previous_attributes'
member.

There is also a "global registry" which is just a list of processors (as defined above)

NOTE: global processors are called before other processors
"""
from collections import defaultdict
from django.utils import six
import functools
import itertools

__all__ = ['handler', 'handler_all', 'call_handlers']


registrations = defaultdict(list)
registrations_global = list()


def handler(event_types):
    """
    Decorator which registers a function as a webhook handler for the given
    types of webhook events
    """
    if isinstance(event_types, six.string_types):
        event_types = [event_types]

    def decorator(func):
        for event_type in event_types:
            registrations[event_type].append(func)
        return func

    return decorator


def handler_all(func=None):
    """
    Decorator which registers a function as a webhook handler for ALL webhook
    events
    """
    if not func:
        return functools.partial(handler_all)

    registrations_global.append(func)
    return func


def call_handlers(event, event_data, event_type, event_subtype):
    qualified_event_type = "%s.%s" % (event_type, event_subtype)
    for handler_func in itertools.chain(
            registrations_global,
            registrations[event_type],
            registrations[qualified_event_type]):
        handler_func(event, event_data, event_type, event_subtype)
