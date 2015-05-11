# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings

import stripe

from .models import Customer


def sync_subscriber(subscriber):
    customer, created = Customer.get_or_create(subscriber=subscriber)
    try:
        cu = customer.stripe_customer
        customer.sync(cu=cu)
        customer.sync_current_subscription(cu=cu)
        customer.sync_invoices(cu=cu)
        customer.sync_charges(cu=cu)
    except stripe.error.InvalidRequestError as e:
        print("ERROR: " + str(e))
    return customer


def sync_plans():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    for plan in settings.DJSTRIPE_PLANS:
        if settings.DJSTRIPE_PLANS[plan].get("stripe_plan_id"):
            try:
                pln = settings.DJSTRIPE_PLANS[plan]
                stripe.Plan.create(
                    amount=pln["price"],
                    interval=pln["interval"],
                    name=pln["name"],
                    currency=pln["currency"],
                    id=pln["stripe_plan_id"],
                    interval_count=pln.get("interval_count"),
                    trial_period_days=pln.get("trial_period_days"),
                    statement_descriptor=pln.get("statement_descriptor"),
                    metadata=pln.get("metadata")
                )
                print("Plan created for {0}".format(plan))
            except Exception as e:
                print("ERROR: " + str(e))
