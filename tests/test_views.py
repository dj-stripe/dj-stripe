"""
.. module:: dj-stripe.tests.test_views
   :synopsis: dj-stripe View Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy

from django.conf import settings
from django.contrib.auth import get_user, get_user_model
from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from django.test.testcases import TestCase
from mock import patch
from stripe.error import StripeError

from djstripe.models import Customer, Subscription, Plan
from djstripe.stripe_objects import StripeSource
from djstripe.views import ChangeCardView
from tests import (
    FAKE_CUSTOMER, FAKE_PLAN, FAKE_PLAN_II, FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_CANCELED, FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END
)


class AccountViewTest(TestCase):

    def setUp(self):
        self.url = reverse("djstripe:account")
        self.user = get_user_model().objects.create_user(
            username="pydanny",
            email="pydanny@gmail.com",
            password="password"
        )
        self.assertTrue(self.client.login(username="pydanny", password="password"))

        Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN_II))

    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    @patch("djstripe.models.djstripe_settings.get_idempotency_key", return_value="foo")
    def test_autocreate_customer(self, idempotency_key_mock, stripe_create_customer_mock):
        self.assertEqual(Customer.objects.count(), 0)

        response = self.client.get(self.url)

        # simply visiting the page should generate a new customer record.
        stripe_create_customer_mock.assert_called_once_with(
            api_key=settings.STRIPE_SECRET_KEY, email=self.user.email, idempotency_key="foo",
            metadata={"djstripe_subscriber": self.user.id}
        )

        self.assertEqual(FAKE_CUSTOMER["id"], response.context["customer"].stripe_id)
        self.assertEqual(self.user, response.context["customer"].subscriber)
        self.assertEqual(Customer.objects.count(), 1)

    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_plans_context(self, stripe_create_customer_mock):
        response = self.client.get(self.url)
        self.assertEqual(list(Plan.objects.all()), list(response.context["plans"]))

    def test_subscription_context_with_plan(self):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))

        response = self.client.get(self.url)
        self.assertEqual(FAKE_SUBSCRIPTION["plan"]["id"], response.context["customer"].subscription.plan.stripe_id)


class ChangeCardViewTest(TestCase):

    def setUp(self):
        self.url = reverse("djstripe:change_card")
        self.user = get_user_model().objects.create_user(
            username="pydanny",
            email="pydanny@gmail.com",
            password="password"
        )
        self.assertTrue(self.client.login(username="pydanny", password="password"))

    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_get(self, stripe_create_customer_mock):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)

    # Needs to be refactored to use sources
    @patch("djstripe.models.Customer.retry_unpaid_invoices", autospec=True)
    @patch("djstripe.models.Customer.send_invoice", autospec=True)
    @patch("djstripe.models.Customer.add_card", autospec=True)
    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_post_new_card(self, stripe_customer_create_mock, add_card_mock, send_invoice_mock,
                           retry_unpaid_invoices_mock):
        self.client.post(self.url, {"stripe_token": "alpha"})
        self.assertEqual(1, Customer.objects.count())
        customer = Customer.objects.get()
        add_card_mock.assert_called_once_with(customer, "alpha")
        send_invoice_mock.assert_called_with(customer)
        retry_unpaid_invoices_mock.assert_called_once_with(customer)

    # Needs to be refactored to use sources
    @patch("djstripe.models.Customer.retry_unpaid_invoices", autospec=True)
    @patch("djstripe.models.Customer.send_invoice", autospec=True)
    @patch("djstripe.models.Customer.add_card", autospec=True)
    def test_post_change_card(self, add_card_mock, send_invoice_mock, retry_unpaid_invoices_mock):
        customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        source = StripeSource.objects.create(customer=customer)
        customer.default_source = source
        customer.save()

        self.assertEqual(1, Customer.objects.count())

        self.client.post(self.url, {"stripe_token": "beta"})
        self.assertEqual(1, Customer.objects.count())
        add_card_mock.assert_called_once_with(customer, "beta")
        self.assertFalse(send_invoice_mock.called)
        retry_unpaid_invoices_mock.assert_called_once_with(customer)

    # Needs to be refactored to use sources
    @patch("djstripe.models.Customer.add_card", autospec=True)
    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_post_card_error(self, stripe_create_customer_mock, add_card_mock):
        add_card_mock.side_effect = StripeError("An error occurred while processing your card.")

        response = self.client.post(self.url, {"stripe_token": "pie"})
        self.assertEqual(1, Customer.objects.count())
        customer = Customer.objects.get()
        add_card_mock.assert_called_once_with(customer, "pie")
        self.assertIn("stripe_error", response.context)
        self.assertIn("An error occurred while processing your card.", response.context["stripe_error"])

    # Needs to be refactored to use sources
    @patch("djstripe.models.Customer.add_card", autospec=True)
    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_post_no_card(self, stripe_create_customer_mock, add_card_mock):
        add_card_mock.side_effect = StripeError("Invalid source object:")

        response = self.client.post(self.url)
        self.assertEqual(1, Customer.objects.count())
        customer = Customer.objects.get()
        add_card_mock.assert_called_once_with(customer, None)
        self.assertIn("stripe_error", response.context)
        self.assertIn("Invalid source object:", response.context["stripe_error"])

    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_get_object(self, stripe_create_customer_mock):
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
        url = view_instance.get_post_success_url()
        self.assertEqual(reverse("djstripe:account"), url)


class CancelSubscriptionViewTest(TestCase):
    def setUp(self):
        self.plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        self.url = reverse("djstripe:cancel_subscription")
        self.user = get_user_model().objects.create_user(
            username="pydanny",
            email="pydanny@gmail.com",
            password="password"
        )
        self.assertTrue(self.client.login(username="pydanny", password="password"))

    @patch("djstripe.stripe_objects.StripeSubscription.cancel", return_value=FAKE_SUBSCRIPTION_CANCELED)
    def test_cancel(self, cancel_subscription_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)

        response = self.client.post(self.url)

        cancel_subscription_mock.assert_called_once_with(at_period_end=True)
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(self.user.is_authenticated())

    @patch("djstripe.stripe_objects.StripeSubscription.cancel", return_value=FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END)
    def test_cancel_at_period_end(self, cancel_subscription_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)

        response = self.client.post(self.url)

        cancel_subscription_mock.assert_called_once_with(at_period_end=True)
        self.assertRedirects(response, reverse("djstripe:account"))
        self.assertTrue(self.user.is_authenticated())

    @patch("djstripe.stripe_objects.StripeSubscription.cancel", return_value=FAKE_SUBSCRIPTION_CANCELED)
    def test_cancel_next_url(self, cancel_subscription_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)

        response = self.client.post(self.url + "?next=/test")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/test")

        self.assertTrue(get_user(self.client).is_anonymous)

    @patch("djstripe.stripe_objects.StripeSubscription.cancel")
    def test_cancel_no_subscription(self, cancel_subscription_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)

        response = self.client.post(self.url)

        cancel_subscription_mock.assert_not_called()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user(self.client).is_anonymous)
