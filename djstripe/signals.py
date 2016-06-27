# -*- coding: utf-8 -*-
from django.dispatch import Signal


webhook_processing_error = Signal(providing_args=["data", "exception"])

# A signal for each Event type. See https://stripe.com/docs/api#event_types

WEBHOOK_SIGNALS = dict([
    (hook, Signal(providing_args=["event"]))
    for hook in [
        "account.updated",
        "account.application.deauthorized",
        "account.external_account.created",
        "account.external_account.deleted",
        "account.external_account.updated",
        "application_fee.created",
        "application_fee.refunded",
        "application_fee.refund.updated",
        "balance.available",
        "bitcoin.receiver.created",
        "bitcoin.receiver.filled",
        "bitcoin.receiver.updated",
        "bitcoin.receiver.transaction.created",
        "charge.captured",
        "charge.failed",
        "charge.refunded",
        "charge.succeeded",
        "charge.updated",
        "charge.dispute.closed",
        "charge.dispute.created",
        "charge.dispute.funds_reinstated",
        "charge.dispute.funds_withdrawn",
        "charge.dispute.updated",
        "coupon.created",
        "coupon.deleted",
        "coupon.updated",
        "customer.created",
        "customer.deleted",
        "customer.updated",
        "customer.discount.created",
        "customer.discount.deleted",
        "customer.discount.updated",
        "customer.source.created",
        "customer.source.deleted",
        "customer.source.updated",
        "customer.subscription.created",
        "customer.subscription.deleted",
        "customer.subscription.trial_will_end",
        "customer.subscription.updated",
        "invoice.created",
        "invoice.payment_failed",
        "invoice.payment_succeeded",
        "invoice.updated",
        "invoiceitem.created",
        "invoiceitem.deleted",
        "invoiceitem.updated",
        "plan.created",
        "plan.deleted",
        "plan.updated",
        "transfer.created",
        "transfer.failed",
        "transfer.paid",
        "transfer.reversed",
        "transfer.updated",
        "ping"
    ]
])
