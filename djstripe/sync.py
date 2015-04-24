# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings

import stripe

from .models import Customer
from .settings import PY3


def sync_subscriber(subscriber_model):
    # TODO - needs tests

    customer, created = Customer.get_or_create(subscriber=subscriber_model)
    try:
        cu = customer.stripe_customer
        customer.sync(cu=cu)
        customer.sync_current_subscription(cu=cu)
        customer.sync_invoices(cu=cu)
        customer.sync_charges(cu=cu)
    except stripe.error.InvalidRequestError as e:
        if PY3:
            print("ERROR: " + str(e))
        else:
            print("ERROR: " + e.message)
    return customer


def sync_plans():
    # TODO - needs tests

    stripe.api_key = settings.STRIPE_SECRET_KEY

    allowed_values = (
        'id',
        'amount',
        'currency',
        'interval',
        'interval_count',
        'name',
        'trial_period_days',
        'metadata',
        'statement_description'
    )
    conversion = {
        'stripe_plan_id': 'id',
        'price': 'amount'
    }

    for plan in settings.DJSTRIPE_PLANS:
        stripe_plan = settings.DJSTRIPE_PLANS[plan]
        if stripe_plan.get("stripe_plan_id"):
            kwargs = {}
            for key in stripe_plan:
                kw_key = conversion.get(key, key)
                if kw_key not in allowed_values:
                    continue
                kwargs[kw_key] = stripe_plan[key]
            try:
                stripe.Plan.create(**kwargs)
                print("Plan created for {0}".format(plan))
            except Exception as e:
                if PY3:
                   print(str(e))
                else:
                   print(e.message)
