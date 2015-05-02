# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from ...models import Customer
from ...settings import get_subscriber_model


class Command(BaseCommand):

    help = "Create customer objects for existing subscribers that don't have one"

    def handle(self, *args, **options):
        for subscriber in get_subscriber_model().objects.filter(customer__isnull=True):
            # use get_or_create in case of race conditions on large subscriber bases
            Customer.get_or_create(subscriber=subscriber)
            print("Created subscriber for {0}".format(subscriber.email))
