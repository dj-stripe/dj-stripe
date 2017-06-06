# -*- coding: utf-8 -*-
"""
.. module:: djstripe.event_handlers.

   :synopsis: dj-stripe - webhook event handlers for the various models

.. moduleauthor:: Bill Huneke (@wahuneke)
.. moduleauthor:: Alex Kavanaugh (@akavanau)
.. moduleauthor:: Lee Skillen (@lskillen)

Stripe docs for Events: https://stripe.com/docs/api#events
Stripe docs for Webhooks: https://stripe.com/docs/webhooks

TODO: Implement webhook event handlers for all the models that need to respond to webhook events.

NOTE: Event data is not guaranteed to be in the correct API version format. See #116.
      When writing a webhook handler, make sure to first re-retrieve the object you wish to
      process.

"""

from . import webhooks
from .enums import SourceType
from .models import (
    Card, Charge, Coupon, Customer, Invoice, InvoiceItem, Plan, Subscription,
    Transfer
)
from .utils import convert_tstamp


@webhooks.handler_all
def customer_event_attach(event, event_data, event_type, event_subtype):
    """Make the related customer available on the event for all handlers to use.

    Does not create Customer objects.
    """
    event.customer = None
    crud_type = CrudType.determine(event_subtype, exact=True)

    if event_type == "customer" and crud_type.valid:
        customer_stripe_id = event_data["object"]["id"]
    else:
        customer_stripe_id = event_data["object"].get("customer", None)

    if customer_stripe_id:
        try:
            event.customer = Customer.objects.get(stripe_id=customer_stripe_id)
        except Customer.DoesNotExist:
            pass


@webhooks.handler("customer")
def customer_webhook_handler(event, event_data, event_type, event_subtype):
    """Handle updates to customer objects.

    First determines the crud_type and then handles the event if a customer exists locally.
    As customers are tied to local users, djstripe will not create customers that
    do not already exist locally.

    Docs and an example customer webhook response: https://stripe.com/docs/api#customer_object
    """
    crud_type = CrudType.determine(event_subtype, exact=True)
    if crud_type.valid and event.customer:
        # As customers are tied to local users, djstripe will not create
        # customers that do not already exist locally.
        _handle_crud_type_event(
            target_cls=Customer,
            event_data=event_data,
            event_subtype=event_subtype,
            crud_type=crud_type
        )


@webhooks.handler("customer.discount")
def customer_discount_webhook_handler(event, event_data, event_type, event_subtype):
    """Handle updates to customer discount objects.

    Docs: https://stripe.com/docs/api#discounts

    Because there is no concept of a "Discount" model in dj-stripe (due to the
    lack of a stripe id on them), this is a little different to the other
    handlers.
    """

    crud_type = CrudType.determine(event_subtype)
    discount_data = event_data["object"]
    coupon_data = discount_data["coupon"]

    if crud_type.created or crud_type.updated:
        coupon, _ = _handle_crud_type_event(
            target_cls=Coupon,
            event_data=coupon_data,
            event_subtype="created",
            stripe_id=coupon_data["id"]
        )
        coupon_start = discount_data["start"]
        coupon_end = discount_data["end"]
    else:
        coupon = None
        coupon_start = None
        coupon_end = None

    event.customer.coupon = coupon
    event.customer.coupon_start = convert_tstamp(coupon_start)
    event.customer.coupon_end = convert_tstamp(coupon_end)
    event.customer.save()


@webhooks.handler("customer.source")
def customer_source_webhook_handler(event, event_data, event_type, event_subtype):
    """Handle updates to customer payment-source objects.

    Docs: https://stripe.com/docs/api#customer_object-sources.
    """
    source_type = event_data["object"]["object"]

    # TODO: handle other types of sources (https://stripe.com/docs/api#customer_object-sources)
    if source_type == SourceType.card:
        _handle_crud_type_event(
            target_cls=Card,
            event_data=event_data,
            event_subtype=event_subtype,
            customer=event.customer
        )


@webhooks.handler("customer.subscription")
def customer_subscription_webhook_handler(event, event_data, event_type, event_subtype):
    """Handle updates to customer subscription objects.

    Docs an example subscription webhook response: https://stripe.com/docs/api#subscription_object
    """
    _handle_crud_type_event(
        target_cls=Subscription,
        event_data=event_data,
        event_subtype=event_subtype,
        customer=event.customer
    )


@webhooks.handler(["transfer", "charge", "coupon", "invoice", "invoiceitem", "plan"])
def other_object_webhook_handler(event, event_data, event_type, event_subtype):
    """Handle updates to transfer, charge, invoice, invoiceitem and plan objects.

    Docs for:
    - charge: https://stripe.com/docs/api#charges
    - coupon: https://stripe.com/docs/api#coupons
    - invoice: https://stripe.com/docs/api#invoices
    - invoiceitem: https://stripe.com/docs/api#invoiceitems
    - plan: https://stripe.com/docs/api#plans
    """
    target_cls = {
        "charge": Charge,
        "coupon": Coupon,
        "invoice": Invoice,
        "invoiceitem": InvoiceItem,
        "plan": Plan,
        "transfer": Transfer
    }.get(event_type)

    _handle_crud_type_event(
        target_cls=target_cls,
        event_data=event_data,
        event_subtype=event_subtype,
        customer=event.customer
    )


#
# Helpers
#

class CrudType(object):
    """Helper object to determine CRUD-like event state."""

    created = False
    updated = False
    deleted = False

    def __init__(self, **kwargs):
        """Set attributes."""
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def valid(self):
        """Return True if this is a CRUD-like event."""
        return self.created or self.updated or self.deleted

    @classmethod
    def determine(cls, event_subtype, exact=False):
        """
        Determine if the event subtype is a crud_type (without the 'R') event.

        :param event_subtype: The event subtype to examine.
        :type event_subtype: string (``str``/`unicode``)
        :param exact: If True, match crud_type to event subtype string exactly.
        :param type: ``bool``
        :returns: The CrudType state object.
        :rtype: ``CrudType``
        """
        def check(crud_type_event):
            if exact:
                return event_subtype == crud_type_event
            else:
                return event_subtype.endswith(crud_type_event)

        created = updated = deleted = False

        if check("updated"):
            updated = True
        elif check("created"):
            created = True
        elif check("deleted"):
            deleted = True

        return cls(created=created, updated=updated, deleted=deleted)


def _handle_crud_type_event(target_cls, event_data, event_subtype, stripe_id=None, customer=None, crud_type=None):
    """
    Helper to process crud_type-like events for objects.

    Non-deletes (creates, updates and "anything else" events) are treated as
    update_or_create events - The object will be retrieved locally, then it is
    synchronised with the Stripe API for parity.

    Deletes only occur for delete events and cause the object to be deleted
    from the local database, if it existed.  If it doesn't exist then it is
    ignored (but the event processing still succeeds).

    :param target_cls: The djstripe model being handled.
    :type: ``djstripe.stripe_objects.StripeObject``
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
            obj = target_cls.objects.get(stripe_id=stripe_id)
            obj.delete()
        except target_cls.DoesNotExist:
            pass
    else:
        # Any other event type (creates, updates, etc.)
        kwargs = {"stripe_id": stripe_id}
        if customer:
            kwargs["customer"] = customer
        data = target_cls(**kwargs).api_retrieve()
        obj = target_cls.sync_from_stripe_data(data)

    return obj, crud_type
