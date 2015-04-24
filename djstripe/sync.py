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
    for plan in settings.DJSTRIPE_PLANS:
        if settings.DJSTRIPE_PLANS[plan].get("stripe_plan_id"):
            try:
                stripe.Plan.create(
                    amount=settings.DJSTRIPE_PLANS[plan]["price"],
                    interval=settings.DJSTRIPE_PLANS[plan]["interval"],
                    name=settings.DJSTRIPE_PLANS[plan]["name"],
                    currency=settings.DJSTRIPE_PLANS[plan]["currency"],
                    id=settings.DJSTRIPE_PLANS[plan].get("stripe_plan_id")
                )
                print("Plan created for {0}".format(plan))
            except Exception as e:
                if PY3:
                    print(str(e))
                else:
                    print(e.message)
