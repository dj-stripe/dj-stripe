"""
Utility functions used for syncing data.
"""

import logging

from stripe import InvalidRequestError

from .models import Customer

logger = logging.getLogger(__name__)


def sync_subscriber(subscriber):
    """Sync a Customer with Stripe api data."""
    customer, _created = Customer.get_or_create(subscriber=subscriber)
    try:
        customer.sync_from_stripe_data(customer.api_retrieve())
        customer._sync_subscriptions()
        customer._sync_invoices()
        customer._sync_charges()
    except InvalidRequestError:
        logger.exception("Failed to sync subscriber %r", subscriber)
    return customer
