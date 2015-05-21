# -*- coding: utf-8 -*-
from django.dispatch import Signal


cancelled = Signal(providing_args=["stripe_response"])
card_changed = Signal(providing_args=["stripe_response"])
subscription_made = Signal(providing_args=["plan", "stripe_response"])
webhook_processing_error = Signal(providing_args=["data", "exception"])

WEBHOOK_SIGNALS = dict([
    (hook, Signal(providing_args=["event"]))
    for hook in [
        "account.updated",
        "account.application.deauthorized",
        "charge.succeeded",
        "charge.failed",
        "charge.refunded",
        "charge.dispute.created",
        "charge.dispute.updated",
        "charge.dispute.closed",
        "customer.created",
        "customer.updated",
        "customer.deleted",
        "customer.source.created",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.trial_will_end",
        "customer.discount.created",
        "customer.discount.updated",
        "customer.discount.deleted",
        "invoice.created",
        "invoice.updated",
        "invoice.payment_succeeded",
        "invoice.payment_failed",
        "invoiceitem.created",
        "invoiceitem.updated",
        "invoiceitem.deleted",
        "plan.created",
        "plan.updated",
        "plan.deleted",
        "coupon.created",
        "coupon.updated",
        "coupon.deleted",
        "transfer.created",
        "transfer.updated",
        "transfer.failed",
        "ping"
    ]
])
