# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings

import stripe

from .models import Customer


def sync_subscriber(subscriber):
    customer, created = Customer.get_or_create(subscriber=subscriber)
    try:
        stripe_customer = customer.stripe_customer
        customer.sync(cu=stripe_customer)
        customer.sync_current_subscription(cu=stripe_customer)
        customer.sync_invoices(cu=stripe_customer)
        customer.sync_charges(cu=stripe_customer)
    except stripe.error.InvalidRequestError as e:
        print("ERROR: " + str(e))
    return customer


def sync_plans(api_key=settings.STRIPE_SECRET_KEY):
    stripe.api_key = api_key
    for plan in settings.DJSTRIPE_PLANS:
        stripe_plan = settings.DJSTRIPE_PLANS[plan]
        if stripe_plan.get("stripe_plan_id"):
            try:
                stripe.Plan.create(
                    amount=stripe_plan["price"],
                    interval=stripe_plan["interval"],
                    name=stripe_plan["name"],
                    currency=stripe_plan["currency"],
                    id=stripe_plan["stripe_plan_id"],
                    interval_count=stripe_plan.get("interval_count"),
                    trial_period_days=stripe_plan.get("trial_period_days"),
                    statement_descriptor=stripe_plan.get("statement_descriptor"),
                    metadata=stripe_plan.get("metadata")
                )
                print("Plan created for {0}".format(plan))
            except Exception as e:
                print("ERROR: " + str(e))
