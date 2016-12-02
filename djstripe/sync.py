# -*- coding: utf-8 -*-
"""
.. module:: djstripe.sync.

  :synopsis: dj-stripe - Utility functions used for syncing data.

.. moduleauthor:: @kavdev, @pydanny, @wahuneke
"""
from __future__ import unicode_literals

from django.conf import settings

from stripe.error import InvalidRequestError

from .models import Customer, Plan


def sync_subscriber(subscriber):
    """Sync a Customer with Stripe api data."""
    customer, _created = Customer.get_or_create(subscriber=subscriber)
    try:
        customer.sync_from_stripe_data(customer.api_retrieve())
        customer._sync_subscriptions()
        customer._sync_invoices()
        customer._sync_charges()
    except InvalidRequestError as e:
        print("ERROR: " + str(e))
    return customer


def sync_plans():
    """Sync plans with Stripe api data."""
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

                Plan._api_create(**api_kwargs)
                print("Plan created for {0}".format(plan))
            except Exception as e:
                print("ERROR: " + str(e))
