"""
Utils related to processing or registering for webhooks

A model registers itself here if it wants to be in the list of processing
functions for a particular webhook. Each processor will have the ability
to modify the event object, access event data, and do what it needs to do

registrations are keyed by top-level event type (e.g. "invoice", "customer", etc)
Each registration entry is a list of processors
Each processor in these lists is a function to be called
The function signature is:
    <Event object>

There is also a "global registry" which is just a list of processors (as defined above)

NOTE: global processors are called before other processors.
"""
import functools
import itertools
from collections import defaultdict

__all__ = ["handler", "handler_all", "call_handlers"]


registrations = defaultdict(list)
registrations_global = []

# Legacy. In previous versions of Stripe API, all test events used this ID.
# Check out issue #779 for more information.
TEST_EVENT_ID = "evt_00000000000000"


def handler(*event_types):
    """
    Decorator that registers a function as a webhook handler.

    Functions can be registered for event types (e.g. 'customer') or
    fully qualified event sub-types (e.g. 'customer.subscription.deleted').

    If an event type is specified, the handler will receive callbacks for
    ALL webhook events of that type.  For example, if 'customer' is specified,
    the handler will receive events for 'customer.subscription.created',
    'customer.subscription.updated', etc.

    :param event_types: The event type(s) that should be handled.
    :type event_types: str.
    """

    def decorator(func):
        for event_type in event_types:
            registrations[event_type].append(func)
        return func

    return decorator


def handler_all(func=None):
    """
    Decorator that registers a function as a webhook handler for ALL webhook events.

    Handles all webhooks regardless of event type or sub-type.
    """
    if not func:
        return functools.partial(handler_all)

    registrations_global.append(func)

    return func


def call_handlers(event):
    """
    Invoke all handlers for the provided event type/sub-type.

    The handlers are invoked in the following order:

    1. Global handlers
    2. Event type handlers
    3. Event sub-type handlers

    Handlers within each group are invoked in order of registration.

    :param event: The event model object.
    :type event: ``djstripe.models.Event``
    """
    chain = [registrations_global]

    # Build up a list of handlers with each qualified part of the event
    # category and verb.  For example, "customer.subscription.created" creates:
    #   1. "customer"
    #   2. "customer.subscription"
    #   3. "customer.subscription.created"
    for index, _ in enumerate(event.parts):
        qualified_event_type = ".".join(event.parts[: (index + 1)])
        chain.append(registrations[qualified_event_type])

    for handler_func in itertools.chain(*chain):
        handler_func(event=event)
