# -*- coding: utf-8 -*-
"""
Utils related to processing or registering for webhooks
"""
from collections import defaultdict

__all__ = ['handler', 'handler_all', 'call_handlers', 'mock_replacement', ]


# A model registers itself here if it wants to be in the list of processing
# functions for a particular webhook. Each processor will have the ability
# to modify the event object, access event data, and do what it needs to do
#
# registrations are keyed by top-level event type (e.g. "invoice", "customer", etc)
# Each registration entry is a list of processors
# Each processor in these lists is a function to be called
# The function signature is: <Event object> <event data dict> <type string> <sub type string>
registrations = defaultdict(list)

# Global handlers, like regular handlers except called for all events.
# NOTE: gobal handlers are called before specific handlers
registrations_global = list()


def handler(f, events):
    """
    Decorator which registers a function as a webhook handler for the given
    types of webhook events
    """
    for event in events:
        registrations[event].append(f)
    return f


def handler_all(f):
    """
    Decorator which registers a function as a webhook handler for ALL webhook
    events
    """
    registrations_global.append(f)
    return f


def call_handlers(event, data, type, sub_type):
    for handler in registrations_global + registrations[type]:
        handler(event, data, type, sub_type)


def mock_replacement(old_func, new_func):
    """
    Search for all handlers that used the old function and replace with call
    to the new function
    """
    lists = [registrations_global, ] + registrations.values()
    for l in lists:
        for i, f in enumerate(l):
            if f == old_func:
                l[i] = new_func
