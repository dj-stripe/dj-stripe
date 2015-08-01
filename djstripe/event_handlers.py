# -*- coding: utf-8 -*-
"""
.. module:: djstripe.event_handlers
   :synopsis: dj-stripe - webhook event handlers for the various models

.. moduleauthor:: Bill Huneke (@wahuneke)

Implement webhook event handlers for all the models that need to respond to webhook events.
"""

from django.utils import timezone

from . import webhooks
from . import settings as djstripe_settings
import stripe
from .models import Customer, CurrentSubscription, Charge, Transfer, Invoice


# ---------------------------
# Customer model events
# ---------------------------
@webhooks.handler_all
def customer_event_attach(event, event_data, event_type, event_subtype):
    stripe_customer_crud_events = ["created", "updated", "deleted"]
    skip_events = ["plan", "transfer"]

    if event_type in skip_events:
        return
    elif event_type == "customer" and event_subtype in stripe_customer_crud_events:
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
        if event_subtype == "subscription.deleted":
            customer.current_subscription.status = CurrentSubscription.STATUS_CANCELLED
            customer.current_subscription.canceled_at = timezone.now()
            customer.current_subscription.save()
        elif event_subtype.startswith("subscription."):
            customer.sync_current_subscription()
        elif event_subtype == "deleted":
            customer.purge()


# ---------------------------
# Transfer model events
# ---------------------------
@webhooks.handler(["transfer"])
def transfer_webhook_handler(event, event_data, event_type, event_subtype):
    # TODO: re-retrieve this transfer object so we have it in proper API version
    Transfer.process_transfer(event, event_data["object"])


# ---------------------------
# Invoice model events
# ---------------------------
@webhooks.handler(['invoice'])
def invoice_webhook_handler(event, event_data, event_type, event_subtype):
    if event_subtype in ["payment_failed", "payment_succeeded", "created"]:
        invoice_data = event_data["object"]
        stripe_invoice = stripe.Invoice.retrieve(invoice_data["id"])
        Invoice.sync_from_stripe_data(stripe_invoice, send_receipt=djstripe_settings.SEND_INVOICE_RECEIPT_EMAILS)


# ---------------------------
# Charge model events
# ---------------------------
@webhooks.handler(['charge'])
def charge_webhook_handler(event, event_data, event_type, event_subtype):
    event_data = stripe.Charge.retrieve(event_data["object"]["id"])
    return Charge.sync_from_stripe_data(event_data)
