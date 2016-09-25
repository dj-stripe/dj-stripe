# -*- coding: utf-8 -*-
"""
.. module:: djstripe.webhooks
   :synopsis: dj-stripe - Utils related to processing or registering for webhooks

.. moduleauthor:: Bill Huneke (@wahuneke)
.. moduleauthor:: Lee Skillen (@lskillen)

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
import functools
import itertools

from django.utils import six

__all__ = ['handler', 'handler_all', 'call_handlers']


registrations = defaultdict(list)
registrations_global = list()


def handler(event_types):
    """
    Decorator which registers a function as a webhook handler for the specified
    event types (e.g. 'customer') or fully qualified event sub-types (e.g.
    'customer.subscription.deleted').

    If an event type is specified then the handler will receive callbacks for
    ALL webhook events of that type.  For example, if 'customer' is specified
    then the handler will receive events for 'customer.subscription.created',
    'customer.subscription.updated', etc.

    :param event_types: The event type(s) or sub-type(s) that should be handled.
    :type event_types: A sequence (`list`) or string (`str`/`unicode`).
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
    events, regardless of event type or sub-type.
    """

    if not func:
        return functools.partial(handler_all)

    registrations_global.append(func)

    return func


def call_handlers(event, event_data, event_type, event_subtype):
    """
    Invokes all handlers for the provided event type/sub-type.

    The handlers are invoked in the following order:

        1. Global handlers
        2. Event type handlers
        3. Event sub-type handlers

    Handlers within each group are invoked in order of registration.

    :param event: The event model object.
    :type event: ``djstripe.models.Event``
    :param event_data: The raw data for the event.
    :type event_data: ``dict``
    :param event_type: The event type, e.g. 'customer'.
    :type event_type: string (``str``/``unicode``)
    :param event_subtype: The event sub-type, e.g. 'updated'.
    :type event_subtype: string (``str``/`unicode``)
    """

    chain = [registrations_global]

    # Build up a list of handlers with each qualified part of the event
    # type and subtype.  For example, "customer.subscription.created" creates:
    #   1. "customer"
    #   2. "customer.subscription"
    #   3. "customer.subscription.created"
    for index, _ in enumerate(event.parts):
        qualified_event_type = ".".join(event.parts[:(index + 1)])
        chain.append(registrations[qualified_event_type])

    for handler_func in itertools.chain(*chain):
        handler_func(event, event_data, event_type, event_subtype)
