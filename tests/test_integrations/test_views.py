"""
.. module:: dj-stripe.tests.test_integrations.test_views
   :synopsis: dj-stripe View Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from django.test.testcases import TestCase

from djstripe import settings as djstripe_settings
from djstripe.models import Customer
from djstripe.views import ChangeCardView, HistoryView


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

    class ChangeCardViewTest(TestCase):

        def setUp(self):
            self.url = reverse("djstripe:change_card")
            self.user = get_user_model().objects.create_user(username="testuser",
                                                             email="test@example.com",
                                                             password="123")
            self.assertTrue(self.client.login(username="testuser", password="123"))

        def test_get(self):
            response = self.client.get(self.url)
            self.assertEqual(200, response.status_code)

        def test_post_new_card(self):
            token = stripe.Token.create(
                card={
                    "number": '4242424242424242',
                    "exp_month": 12,
                    "exp_year": 2016,
                    "cvc": '123'
                },
            )

            self.client.post(self.url, {"stripe_token": token.id})
            customer_instance = Customer.objects.get(subscriber=self.user)
            self.assertEqual(token.card.fingerprint, customer_instance.card_fingerprint)

        def test_post_change_card(self):
            token_a = stripe.Token.create(
                card={
                    "number": '4242424242424242',
                    "exp_month": 12,
                    "exp_year": 2016,
                    "cvc": '123'
                },
            )
            self.client.post(self.url, {"stripe_token": token_a.id})

            token_b = stripe.Token.create(
                card={
                    "number": '4000000000000077',
                    "exp_month": 12,
                    "exp_year": 2016,
                    "cvc": '123'
                },
            )

            self.client.post(self.url, {"stripe_token": token_b.id})
            customer_instance = Customer.objects.get(subscriber=self.user)
            self.assertEqual(token_b.card.fingerprint, customer_instance.card_fingerprint)

        def test_post_card_error(self):
            token = stripe.Token.create(
                card={
                    "number": '4000000000000119',
                    "exp_month": 12,
                    "exp_year": 2016,
                    "cvc": '123'
                },
            )

            response = self.client.post(self.url, {"stripe_token": token.id})
            self.assertIn("stripe_error", response.context)
            self.assertIn("An error occurred while processing your card.", response.context["stripe_error"])

        def test_post_no_card(self):
            response = self.client.post(self.url)
            self.assertIn("stripe_error", response.context)
            self.assertIn("Invalid source object:", response.context["stripe_error"])

        def test_get_object(self):
            view_instance = ChangeCardView()
            request = RequestFactory()
            request.user = self.user

            view_instance.request = request
            object_a = view_instance.get_object()
            object_b = view_instance.get_object()

            customer_instance = Customer.objects.get(subscriber=self.user)
            self.assertEqual(customer_instance, object_a)
            self.assertEqual(object_a, object_b)

        def test_get_success_url(self):
            view_instance = ChangeCardView()
            view_instance.get_post_success_url()

    class HistoryViewTest(TestCase):

        def setUp(self):
            self.url = reverse("djstripe:history")
            self.user = get_user_model().objects.create_user(username="testuser",
                                                             email="test@example.com",
                                                             password="123")
            self.assertTrue(self.client.login(username="testuser", password="123"))

        def test_get_object(self):
            view_instance = HistoryView()
            request = RequestFactory()
            request.user = self.user

            view_instance.request = request
            object_a = view_instance.get_object()

            customer_instance = Customer.objects.get(subscriber=self.user)
            self.assertEqual(customer_instance, object_a)

    class SyncHistoryViewTest(TestCase):

        def setUp(self):
            self.url = reverse("djstripe:sync_history")
            self.user = get_user_model().objects.create_user(username="testuser",
                                                             email="test@example.com",
                                                             password="123")
            self.assertTrue(self.client.login(username="testuser", password="123"))

        def test_post(self):
            response = self.client.post(self.url)
            self.assertEqual(self.user, response.context["customer"].subscriber)
