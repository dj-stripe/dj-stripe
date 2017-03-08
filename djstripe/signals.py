# -*- coding: utf-8 -*-
"""
.. module:: djstripe.signals.

   :synopsis: dj-stripe - signals are sent for each event Stripe sends to the app

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

Stripe docs for Webhooks: https://stripe.com/docs/webhooks
"""

from django.dispatch import Signal, receiver
from django.db.models.signals import pre_delete
from . import settings as djstripe_settings


def stripe_receiver(signal, **kwargs):
    """
    A stripe version of the django signal receiver::

        @stripe_receiver('account.updated')
        def signal_receiver(event, **kwargs):
            ...

        @stripe_receiver(['customer.created', 'customer.updated'])
        def signal_receiver(event, **kwargs):
            ...
    """
    def _decorator(func):
        if isinstance(signal, (list, tuple)):
            for s in signal:
                WEBHOOK_SIGNALS[s].connect(func, **kwargs)
        else:
            WEBHOOK_SIGNALS[signal].connect(func, **kwargs)
        return func

    return _decorator


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


@receiver(pre_delete, sender=djstripe_settings.get_subscriber_model_string())
def on_delete_subscriber_purge_customer(instance=None, **kwargs):
    """ Purge associated customers when the subscriber is deleted. """
    for customer in instance.djstripe_customers.all():
        customer.purge()
