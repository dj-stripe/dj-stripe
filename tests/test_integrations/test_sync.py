"""
.. module:: dj-stripe.tests.test_integrations.test_sync
   :synopsis: dj-stripe Sync Method Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

import sys

from django.conf import settings
from django.test.testcases import TestCase
from django.contrib.auth import get_user_model

from stripe.error import InvalidRequestError

from djstripe.models import Charge
from djstripe.sync import sync_subscriber, sync_plans

if settings.STRIPE_PUBLIC_KEY and settings.STRIPE_SECRET_KEY:
    class TestSyncSubscriber(TestCase):

        def setUp(self):
            self.user = get_user_model().objects.create_user(username="testsync", email="testsync@test.com")

        def test_new_customer(self):
            customer = sync_subscriber(self.user)
            charges = Charge.objects.filter(customer=customer)

            # There shouldn't be any items attached to the customer
            self.assertEqual(0, len(charges), "Charges are unexpectedly associated with a new customer object.")
            customer.purge()

        def test_existing_customer(self):
            customerA = sync_subscriber(self.user)
            customerB = sync_subscriber(self.user)

            self.assertEqual(customerA, customerB, "Customers returned are not equal.")

            customerA.purge()
            customerB.purge()

        def test_bad_sync(self):
            customer = sync_subscriber(self.user)
            customer.stripe_id = "fake_customer_id"
            customer.save()

            sync_subscriber(self.user)

            self.assertEqual("ERROR: No such customer: fake_customer_id", sys.stdout.getvalue().strip())

            customer.purge()

        def test_charge_sync(self):
            # Initialize stripe
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            customer = sync_subscriber(self.user)
            charges = Charge.objects.filter(customer=customer)

            # There shouldn't be any items attached to the customer
            self.assertEqual(0, len(charges), "Charges are unexpectedly associated with a new customer object.")

            token = stripe.Token.create(
                card={
                    "number": '4242424242424242',
                    "exp_month": 12,
                    "exp_year": 2016,
                    "cvc": '123'
                },
            )

            customer.update_card(token.id)

            stripe.Charge.create(
                amount=int(10 * 100),  # Convert dollars into cents
                currency="USD",
                customer=customer.stripe_id,
                description="Test Charge in test_charge_sync",
            )

            customer = sync_subscriber(self.user)
            charges = Charge.objects.filter(customer=customer)
            self.assertEqual(1, len(charges), "Unexpected number of charges associated with a new customer object.")

            customer.purge()

    class TestSyncPlans(TestCase):

        def test_simple_sync(self):
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Delete all plans
            for plan in stripe.Plan.all()["data"]:
                try:
                    plan.delete()
                except InvalidRequestError:
                    continue

            sync_plans()
            self.assertTrue("Plan created for test", sys.stdout.getvalue().strip())

            sync_plans()
            self.assertTrue("ERROR: Plan already exists.", sys.stdout.getvalue().strip())
