# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from ...models import DJStripeCustomer
from ...settings import get_customer_model


class Command(BaseCommand):

    help = "Create djstripecustomer objects for existing customers that don't have one"

    def handle(self, *args, **options):
        for customer in get_customer_model().objects.filter(djstripecustomer__isnull=True):
            # use get_or_create in case of race conditions on large customer bases
            DJStripeCustomer.get_or_create(customer=customer)
            print("Created customer for {0}".format(customer.email))
