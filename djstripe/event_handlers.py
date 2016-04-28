# -*- coding: utf-8 -*-
"""
.. module:: djstripe.event_handlers
   :synopsis: dj-stripe - webhook event handlers for the various models

.. moduleauthor:: Bill Huneke (@wahuneke)

Implement webhook event handlers for all the models that need to respond to webhook events.

"""

from . import webhooks
from . import settings as djstripe_settings
from .models import Charge, Customer, Card, Subscription, Plan, Transfer, Invoice


# ---------------------------
# Charge model events
# ---------------------------
@webhooks.handler(['charge'])
def charge_webhook_handler(event, event_data, event_type, event_subtype):
    Charge.sync_from_stripe_data(event_data["object"])


# ---------------------------
# Customer model events
# ---------------------------
@webhooks.handler_all
def customer_event_attach(event, event_data, event_type, event_subtype):
    stripe_customer_crud_events = ["created", "updated", "deleted"]

    if event_type == "customer" and event_subtype in stripe_customer_crud_events:
        stripe_customer_id = event_data["object"]["id"]
    else:
        stripe_customer_id = event_data["object"].get("customer", None)

    if stripe_customer_id:
        try:
            event.customer = Customer.objects.get(stripe_id=stripe_customer_id)
        except Customer.DoesNotExist:
            pass


@webhooks.handler(['customer'])
def customer_webhook_handler(event, event_data, event_type, event_subtype):
    stripe_customer_crud_events = ["created", "updated", "deleted"]

    customer = event.customer
    if customer:
        if event_subtype in stripe_customer_crud_events:
            Customer.sync_from_stripe_data(event_data)
        elif event_subtype.startswith("discount."):
            pass  # TODO
        elif event_subtype.startswith("source."):
            source_type = event_data["object"]["object"]

            # TODO: other sources
            if source_type == "card":
                Card.sync_from_stripe_data(event_data["object"])
        elif event_subtype.startswith("subscription."):
            Subscription.sync_from_stripe_data(event_data["object"])
        elif event_subtype == "deleted":
            customer.purge()


# ---------------------------
# Coupon model events
# ---------------------------

# TODO


# ---------------------------
# Invoice model events
# ---------------------------
@webhooks.handler(['invoice'])
def invoice_webhook_handler(event, event_data, event_type, event_subtype):
    Invoice.sync_from_stripe_data(event_data["object"], send_receipt=djstripe_settings.SEND_INVOICE_RECEIPT_EMAILS)


# ---------------------------
# InvoiceItem model events
# ---------------------------

# TODO


# ---------------------------
# Plan model events
# ---------------------------
@webhooks.handler(['plan'])
def plan_webhook_handler(event, event_data, event_type, event_subtype):
    Plan.sync_from_stripe_data(event_data["object"], send_receipt=djstripe_settings.SEND_INVOICE_RECEIPT_EMAILS)


# ---------------------------
# Transfer model events
# ---------------------------
@webhooks.handler(["transfer"])
def transfer_webhook_handler(event, event_data, event_type, event_subtype):
    # TODO: update when transfer is fixed
    Transfer.process_transfer(event, event_data["object"])
