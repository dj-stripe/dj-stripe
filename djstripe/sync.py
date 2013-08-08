from __future__ import unicode_literals

import stripe

from .models import Customer


def sync_customer(user):
    # TODO - needs tests
    customer, created = Customer.get_or_create(user)
    cu = customer.stripe_customer
    customer.sync(cu=cu)
    customer.sync_current_subscription(cu=cu)
    customer.sync_invoices(cu=cu)
    customer.sync_charges(cu=cu)
    return customer

