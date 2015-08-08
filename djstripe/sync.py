# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings

from stripe.error import InvalidRequestError

from .models import Customer, Plan


def sync_subscriber(subscriber):
    customer, created = Customer.get_or_create(subscriber=subscriber)
    try:
        customer.sync()
        customer.sync_current_subscription()
        customer.sync_invoices()
        customer.sync_charges()
    except InvalidRequestError as e:
        print("ERROR: " + str(e))
    return customer


def sync_plans():
    for plan in settings.DJSTRIPE_PLANS:
        stripe_plan = settings.DJSTRIPE_PLANS[plan]
        if stripe_plan.get("stripe_plan_id"):
            try:
                # A few minor things are changed in the api-version of the create call
                api_kwargs = dict(stripe_plan)
                api_kwargs['id'] = api_kwargs['stripe_plan_id']
                api_kwargs['amount'] = api_kwargs['price']
                del(api_kwargs['stripe_plan_id'])
                del(api_kwargs['price'])
                del(api_kwargs['description'])

                Plan.api_create(**api_kwargs)
                print("Plan created for {0}".format(plan))
            except Exception as e:
                print("ERROR: " + str(e))
