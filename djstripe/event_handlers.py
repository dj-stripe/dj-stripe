# -*- coding: utf-8 -*-
"""
.. module:: djstripe.event_handlers
   :synopsis: dj-stripe - webhook event handlers for the various models

.. moduleauthor:: Bill Huneke (@wahuneke)

Implement webhook event handlers for all the models that need to respond to webhook events.

NOTE: Event data is not guaranteed to be in the correct API version format. See #116.
      When writing a webhook handler, make sure to first re-retrieve the object you wish to
      process.

"""

from . import settings as djstripe_settings
from . import webhooks
from .models import Charge, Customer, Card, Subscription, Plan, Transfer, Invoice


# ---------------------------
# Charge model events
# ---------------------------
@webhooks.handler(['charge'])
def charge_webhook_handler(event, event_data, event_type, event_subtype):
    versioned_charge_data = Charge(stripe_id=event_data["object"]["id"]).api_retrieve()
    Charge.sync_from_stripe_data(versioned_charge_data)


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
# Invoice model events
# ---------------------------
@webhooks.handler(['invoice'])
def invoice_webhook_handler(event, event_data, event_type, event_subtype):
    versioned_invoice_data = Invoice(stripe_id=event_data["object"]["id"]).api_retrieve()
    Invoice.sync_from_stripe_data(versioned_invoice_data, send_receipt=djstripe_settings.SEND_INVOICE_RECEIPT_EMAILS)


# ---------------------------
# InvoiceItem model events
# ---------------------------

# TODO


# ---------------------------
# Plan model events
# ---------------------------
@webhooks.handler(['plan'])
def plan_webhook_handler(event, event_data, event_type, event_subtype):
    versioned_plan_data = Plan(stripe_id=event_data["object"]["id"]).api_retrieve()
    Plan.sync_from_stripe_data(versioned_plan_data)


# ---------------------------
# Transfer model events
# ---------------------------
@webhooks.handler(["transfer"])
def transfer_webhook_handler(event, event_data, event_type, event_subtype):
    versioned_transfer_data = Transfer(stripe_id=event_data["object"]["id"]).api_retrieve()
    Transfer.sync_from_stripe_data(versioned_transfer_data)
