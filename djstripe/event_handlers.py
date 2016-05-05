# -*- coding: utf-8 -*-
"""
.. module:: djstripe.event_handlers
   :synopsis: dj-stripe - webhook event handlers for the various models

.. moduleauthor:: Bill Huneke (@wahuneke)
.. moduleauthor:: Alex Kavanaugh (@akavanau)

Implement webhook event handlers for all the models that need to respond to webhook events.

NOTE: Event data is not guaranteed to be in the correct API version format. See #116.
      When writing a webhook handler, make sure to first re-retrieve the object you wish to
      process.

"""

from . import webhooks
from .models import Charge, Customer, Card, Subscription, Plan, Transfer, Invoice, InvoiceItem

STRIPE_CRUD_EVENTS = ["created", "updated", "deleted"]


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

    if event_type == "customer" and event_subtype in STRIPE_CRUD_EVENTS:
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

    customer = event.customer
    if customer:
        if event_subtype in STRIPE_CRUD_EVENTS:
            versioned_customer_data = Customer(stripe_id=event_data["object"]["id"]).api_retrieve()
            Customer.sync_from_stripe_data(versioned_customer_data)

            if event_subtype == "deleted":
                customer.purge()
#         elif event_subtype.startswith("discount."):
#             pass  # TODO
        elif event_subtype.startswith("source."):
            source_type = event_data["object"]["object"]

            # TODO: other sources
            if source_type == "card":
                versioned_card_data = Card(stripe_id=event_data["object"]["id"], customer=customer).api_retrieve()
                Card.sync_from_stripe_data(versioned_card_data)
        elif event_subtype.startswith("subscription."):
            versioned_subscription_data = Subscription(stripe_id=event_data["object"]["id"], customer=customer).api_retrieve()
            Subscription.sync_from_stripe_data(versioned_subscription_data)


# ---------------------------
# Transfer model events
# ---------------------------
@webhooks.handler(["transfer"])
def transfer_webhook_handler(event, event_data, event_type, event_subtype):
    versioned_transfer_data = Transfer(stripe_id=event_data["object"]["id"]).api_retrieve()
    Transfer.sync_from_stripe_data(versioned_transfer_data)


# ---------------------------
# Invoice model events
# ---------------------------
@webhooks.handler(['invoice'])
def invoice_webhook_handler(event, event_data, event_type, event_subtype):
    versioned_invoice_data = Invoice(stripe_id=event_data["object"]["id"]).api_retrieve()
    Invoice.sync_from_stripe_data(versioned_invoice_data)


# ---------------------------
# InvoiceItem model events
# ---------------------------
@webhooks.handler(['invoiceitem'])
def invoiceitem_webhook_handler(event, event_data, event_type, event_subtype):
    versioned_invoiceitem_data = InvoiceItem(stripe_id=event_data["object"]["id"]).api_retrieve()
    InvoiceItem.sync_from_stripe_data(versioned_invoiceitem_data)


# ---------------------------
# Plan model events
# ---------------------------
@webhooks.handler(['plan'])
def plan_webhook_handler(event, event_data, event_type, event_subtype):
    versioned_plan_data = Plan(stripe_id=event_data["object"]["id"]).api_retrieve()
    Plan.sync_from_stripe_data(versioned_plan_data)


