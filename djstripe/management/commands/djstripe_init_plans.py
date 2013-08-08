from __future__ import unicode_literals
from django.conf import settings
from django.core.management.base import BaseCommand

import stripe


class Command(BaseCommand):

    help = "Make sure your Stripe account has the plans"

    def handle(self, *args, **options):
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
                    print(e.message)
