# -*- coding: utf-8 -*-
"""
.. module:: djstripe.event_handlers
   :synopsis: dj-stripe - webhook event handlers for the various models

.. moduleauthor:: Bill Huneke (@wahuneke)
.. moduleauthor:: Alex Kavanaugh (@akavanau)
.. moduleauthor:: Lee Skillen (@lskillen)

Implement webhook event handlers for all the models that need to respond to webhook events.

NOTE: Event data is not guaranteed to be in the correct API version format. See #116.
      When writing a webhook handler, make sure to first re-retrieve the object you wish to
      process.

"""

from . import webhooks
from .models import Charge, Customer, Card, Subscription, Plan, Transfer, Invoice, InvoiceItem


@webhooks.handler_all
def customer_event_attach(event, event_data, event_type, event_subtype):
    """ Makes the related customer available on the event for all handlers. """
    event.customer = None
    crud_type = CrudType.determine(event_subtype, exact=True)

    if event_type == "customer" and crud_type.valid:
        customer_stripe_id = event_data["object"]["id"]
    else:
        customer_stripe_id = event_data["object"].get("customer", None)

    if not customer_stripe_id:
        return

    try:
        event.customer = Customer.objects.get(stripe_id=customer_stripe_id)
    except Customer.DoesNotExist:
        pass


@webhooks.handler("customer")
def customer_webhook_handler(
        event, event_data, event_type, event_subtype):
    """ Handles updates for customer objects. """
    crud_type = CrudType.determine(event_subtype, exact=True)
    if not crud_type.valid:
        return

    if not event.customer:
        # As customers are tied to local users, djstripe will not create
        # customers that do not already exist locally.
        return

    if crud_type.deleted:
        # Deletions for customers are handled a little bit differently, since
        # the customer is "purged" but not fully deleted from the system, so
        # the object is updated first then "deleted".
        _handle_crud_type_event(
            Customer, event_data, event_subtype,
            crud_type=CrudType(updated=True))

    _handle_crud_type_event(
        Customer, event_data, event_subtype, crud_type=crud_type)


@webhooks.handler("customer.source")
def customer_source_webhook_handler(
        event, event_data, event_type, event_subtype):
    """ Handles updates for customer source objects. """
    source_type = event_data["object"]["object"]

    # TODO: other sources
    if source_type != "card":
        return

    obj, crud_type = _handle_crud_type_event(
        Card, event_data, event_subtype, customer=event.customer)


@webhooks.handler("customer.subscription")
def customer_subscription_webhook_handler(
        event, event_data, event_type, event_subtype):
    """ Handles updates for subscription objects. """
    _handle_crud_type_event(
        Subscription, event_data, event_subtype, customer=event.customer)


@webhooks.handler("transfer")
def transfer_webhook_handler(event, event_data, event_type, event_subtype):
    """ Handles updates for transfer objects. """
    _handle_crud_type_event(Transfer, event_data, event_subtype)


@webhooks.handler(["charge"])
def charge_webhook_handler(event, event_data, event_type, event_subtype):
    """ Handles updates for charge objects. """
    _handle_crud_type_event(Charge, event_data, event_subtype)


@webhooks.handler("invoice")
def invoice_webhook_handler(event, event_data, event_type, event_subtype):
    """ Handles updates for invoice objects. """
    _handle_crud_type_event(Invoice, event_data, event_subtype)


@webhooks.handler("invoiceitem")
def invoiceitem_webhook_handler(event, event_data, event_type, event_subtype):
    """ Handles updates for invoice item objects. """
    _handle_crud_type_event(InvoiceItem, event_data, event_subtype)


@webhooks.handler("plan")
def plan_webhook_handler(event, event_data, event_type, event_subtype):
    """ Handles updates for plan objects. """
    _handle_crud_type_event(Plan, event_data, event_subtype)


#
# Helpers
#

class CrudType(object):
    """ Helper object to determine CRUD-like event state. """
    created = False
    updated = False
    deleted = False

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    @property
    def valid(self):
        """ Returns True if this is a CRUD-like event. """
        return self.created or self.updated or self.deleted

    @classmethod
    def determine(cls, event_subtype, exact=False):
        """
        Determines if the event subtype is a crud_type (without the 'R') event.

        :param event_subtype: The event subtype to examine.
        :param exact: If True, match crud_type to event subtype string exactly.
        :returns: The CrudType state object.
        :rtype: ``CrudType``
        """
        crud_type = cls()

        def check(crud_type_event):
            if exact:
                return event_subtype == crud_type_event
            else:
                return event_subtype.endswith(crud_type_event)

        if check("updated"):
            crud_type.updated = True
        elif check("created"):
            crud_type.created = True
        elif check("deleted"):
            crud_type.deleted = True

        return crud_type


def _handle_crud_type_event(
        cls, event_data, event_subtype, stripe_id=None, customer=None,
        crud_type=None):
    """
    Helper to process crud_type-like events for objects.

    Non-deletes (creates, updates and "anything else" events) are treated as
    update_or_create events - The object will be retrieved locally, then it is
    synchronised with the Stripe API for parity.

    Deletes only occur for delete events and cause the object to be deleted
    from the local database, if it existed.  If it doesn't exist then it is
    ignored (but the event processing still succeeds).

    :param event_data: The event object data received from the Stripe API.
    :param event_subtype: The event subtype string.
    :param stripe_id: The object Stripe ID - If not provided then this is
    retrieved from the event object data by "object.id" key.
    :param customer: The customer object which is passed on object creation.
    :param crud_type: The CrudType object - If not provided it is determined
    based on the event subtype string.
    :returns: The object (if any) and the event CrudType.
    :rtype: ``tuple(obj, CrudType)``
    """
    crud_type = crud_type or CrudType.determine(event_subtype)
    stripe_id = stripe_id or event_data["object"]["id"]
    obj = None

    if crud_type.deleted:
        try:
            obj = cls.objects.get(stripe_id=stripe_id)
            obj.delete()
        except cls.DoesNotExist:
            pass
    else:
        # Any other event type (creates, updates, etc.)
        kwargs = {"stripe_id": stripe_id}
        if customer:
            kwargs["customer"] = customer
        data = cls(**kwargs).api_retrieve()
        obj = cls.sync_from_stripe_data(data)

    return obj, crud_type
