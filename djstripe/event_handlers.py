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
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from . import webhooks
from .enums import SourceType
from .models import (
    Card, Charge, Coupon, Customer, Dispute, Invoice, InvoiceItem, PaymentMethod, Plan, Subscription, Transfer
)
from .utils import convert_tstamp


logger = logging.getLogger(__name__)


@webhooks.handler("customer")
def customer_webhook_handler(event):
    """Handle updates to customer objects.

    First determines the crud_type and then handles the event if a customer exists locally.
    As customers are tied to local users, djstripe will not create customers that
    do not already exist locally.

    Docs and an example customer webhook response: https://stripe.com/docs/api#customer_object
    """
    if event.customer:
        # As customers are tied to local users, djstripe will not create
        # customers that do not already exist locally.
        _handle_crud_like_event(target_cls=Customer, event=event, crud_exact=True, crud_valid=True)


@webhooks.handler("customer.discount")
def customer_discount_webhook_handler(event):
    """Handle updates to customer discount objects.

    Docs: https://stripe.com/docs/api#discounts

    Because there is no concept of a "Discount" model in dj-stripe (due to the
    lack of a stripe id on them), this is a little different to the other
    handlers.
    """

    crud_type = CrudType.determine(event=event)
    discount_data = event.data.get("object", {})
    coupon_data = discount_data.get("coupon", {})
    customer = event.customer

    if crud_type.created or crud_type.updated:
        coupon, _ = _handle_crud_like_event(
            target_cls=Coupon,
            event=event,
            data=coupon_data,
            stripe_id=coupon_data.get("id")
        )
        coupon_start = discount_data.get("start")
        coupon_end = discount_data.get("end")
    else:
        coupon = None
        coupon_start = None
        coupon_end = None

    customer.coupon = coupon
    customer.coupon_start = convert_tstamp(coupon_start)
    customer.coupon_end = convert_tstamp(coupon_end)
    customer.save()


@webhooks.handler("customer.source")
def customer_source_webhook_handler(event):
    """Handle updates to customer payment-source objects.

    Docs: https://stripe.com/docs/api#customer_object-sources.
    """
    customer_data = event.data.get("object", {})
    source_type = customer_data.get("object", {})

    # TODO: handle other types of sources (https://stripe.com/docs/api#customer_object-sources)
    if source_type == SourceType.card:
        if event.verb.endswith("deleted") and customer_data:
            # On customer.source.deleted, we do not delete the object, we merely unlink it.
            # customer = Customer.objects.get(stripe_id=customer_data["id"])
            # NOTE: for now, customer.sources still points to Card
            # Also, https://github.com/dj-stripe/dj-stripe/issues/576
            Card.objects.filter(stripe_id=customer_data.get("id", "")).delete()
            PaymentMethod.objects.filter(id=customer_data.get("id", "")).delete()
        else:
            _handle_crud_like_event(target_cls=Card, event=event)


@webhooks.handler("customer.subscription")
def customer_subscription_webhook_handler(event):
    """Handle updates to customer subscription objects.

    Docs an example subscription webhook response: https://stripe.com/docs/api#subscription_object
    """
    _handle_crud_like_event(target_cls=Subscription, event=event)


@webhooks.handler("transfer", "charge", "coupon", "invoice", "invoiceitem", "plan")
def other_object_webhook_handler(event):
    """Handle updates to transfer, charge, invoice, invoiceitem and plan objects.

    Docs for:
    - charge: https://stripe.com/docs/api#charges
    - coupon: https://stripe.com/docs/api#coupons
    - invoice: https://stripe.com/docs/api#invoices
    - invoiceitem: https://stripe.com/docs/api#invoiceitems
    - plan: https://stripe.com/docs/api#plans
    """

    if event.parts[:2] == ["charge", "dispute"]:
        # Do not attempt to handle charge.dispute.* events.
        # We do not have a Dispute model yet.
        target_cls = Dispute
    else:
        target_cls = {
            "charge": Charge,
            "coupon": Coupon,
            "invoice": Invoice,
            "invoiceitem": InvoiceItem,
            "plan": Plan,
            "transfer": Transfer
        }.get(event.category)

    _handle_crud_like_event(target_cls=target_cls, event=event)


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
    def determine(cls, event, verb=None, exact=False):
        """
        Determine if the event verb is a crud_type (without the 'R') event.

        :param verb: The event verb to examine.
        :type verb: string (``str``/`unicode``)
        :param exact: If True, match crud_type to event verb string exactly.
        :param type: ``bool``
        :returns: The CrudType state object.
        :rtype: ``CrudType``
        """
        verb = verb or event.verb

        def check(crud_type_event):
            if exact:
                return verb == crud_type_event
            else:
                return verb.endswith(crud_type_event)

        created = updated = deleted = False

        if check("updated"):
            updated = True
        elif check("created"):
            created = True
        elif check("deleted"):
            deleted = True

        return cls(created=created, updated=updated, deleted=deleted)


def _handle_crud_like_event(target_cls, event, data=None, verb=None,
                            stripe_id=None, customer=None, crud_type=None,
                            crud_exact=False, crud_valid=False):
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
    :param data: The event object data (defaults to ``event.data``).
    :param verb: The event verb (defaults to ``event.verb``).
    :param stripe_id: The object Stripe ID (defaults to ``object.id``).
    :param customer: The customer object (defaults to ``event.customer``).
    :param crud_type: The CrudType object (determined by default).
    :param crud_exact: If True, match verb against CRUD type exactly.
    :param crud_valid: If True, CRUD type must match valid type.
    :returns: The object (if any) and the event CrudType.
    :rtype: ``tuple(obj, CrudType)``
    """
    data = data or event.data
    stripe_id = stripe_id or data.get("object", {}).get("id", None)

    if not stripe_id:
        # We require an object when applying CRUD-like events, so if there's
        # no ID the event is ignored/dropped. This happens in events such as
        # invoice.upcoming, which refer to a future (non-existant) invoice.
        logger.debug(
            "Ignoring %r Stripe event without object ID: %r",
            event.type, event)
        return

    verb = verb or event.verb
    customer = customer or event.customer
    crud_type = crud_type or CrudType.determine(event=event, verb=verb, exact=crud_exact)
    obj = None

    if crud_valid and not crud_type.valid:
        logger.debug(
            "Ignoring %r Stripe event without valid CRUD type: %r",
            event.type, event)
        return

    if crud_type.deleted:
        qs = target_cls.objects.filter(stripe_id=stripe_id)
        if target_cls is Customer and qs.exists():
            qs.get().purge()
        else:
            obj = target_cls.objects.filter(stripe_id=stripe_id).delete()
    else:
        # Any other event type (creates, updates, etc.) - This can apply to
        # verbs that aren't strictly CRUD but Stripe do intend an update.  Such
        # as invoice.payment_failed.
        kwargs = {"stripe_id": stripe_id}
        if hasattr(target_cls, 'customer'):
            kwargs["customer"] = customer
        data = target_cls(**kwargs).api_retrieve()
        obj = target_cls.sync_from_stripe_data(data)

    return obj, crud_type
