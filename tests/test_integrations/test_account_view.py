"""
.. module:: dj-stripe.tests.test_integrations.test_account_view
   :synopsis: dj-stripe AccountView Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test.testcases import TestCase

from djstripe import settings as djstripe_settings
from djstripe.models import Customer


if settings.STRIPE_PUBLIC_KEY and settings.STRIPE_SECRET_KEY:
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    class AccountViewTest(TestCase):
        def setUp(self):
            self.url = reverse("djstripe:account")
            self.user = get_user_model().objects.create_user(username="testuser",
                                                             email="test@example.com",
                                                             password="123")
            self.assertTrue(self.client.login(username="testuser", password="123"))

        def test_autocreate_customer(self):
            self.assertEqual(Customer.objects.count(), 0)

            response = self.client.get(self.url)

            # simply visiting the page should generate a new customer record.
            self.assertEqual(self.user, response.context["customer"].subscriber)
            self.assertEqual(Customer.objects.count(), 1)

        def test_plan_list_context(self):
            response = self.client.get(self.url)
            self.assertEqual(djstripe_settings.PLAN_LIST, response.context["plans"])

        def test_subscription_context(self):
            response = self.client.get(self.url)
            self.assertEqual(None, response.context["subscription"])

            customer = response.context["customer"]

            token = stripe.Token.create(
                card={
                    "number": '4242424242424242',
                    "exp_month": 12,
                    "exp_year": 2016,
                    "cvc": '123'
                },
            )
            customer.update_card(token.id)

            customer.subscribe(plan="test0")
            response = self.client.get(self.url)
            self.assertEqual("test0", response.context["subscription"].plan)
