"""
.. module:: dj-stripe.tests.test_views
   :synopsis: dj-stripe View Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from django.test.testcases import TestCase
from django.utils import timezone
from mock import patch, PropertyMock
from stripe.error import StripeError

from djstripe.models import Customer, Subscription, Plan
from djstripe.stripe_objects import StripeSource
from djstripe.views import ChangeCardView, HistoryView
from tests import FAKE_CUSTOMER, FAKE_SUBSCRIPTION, FAKE_PLAN, FAKE_PLAN_II, FAKE_SUBSCRIPTION_II


class AccountViewTest(TestCase):

    def setUp(self):
        self.url = reverse("djstripe:account")
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com", password="password")
        self.assertTrue(self.client.login(username="pydanny", password="password"))

        Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN_II))

    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_autocreate_customer(self, stripe_create_customer_mock):
        self.assertEqual(Customer.objects.count(), 0)

        response = self.client.get(self.url)

        # simply visiting the page should generate a new customer record.
        stripe_create_customer_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, email=self.user.email)

        self.assertEqual(FAKE_CUSTOMER["id"], response.context["customer"].stripe_id)
        self.assertEqual(self.user, response.context["customer"].subscriber)
        self.assertEqual(Customer.objects.count(), 1)

    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_plans_context(self, stripe_create_customer_mock):
        response = self.client.get(self.url)
        self.assertEqual(list(Plan.objects.all()), list(response.context["plans"]))

    def test_subscription_context_with_plan(self):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))

        response = self.client.get(self.url)
        self.assertEqual(FAKE_SUBSCRIPTION["plan"]["id"], response.context["customer"].subscription.plan.stripe_id)


class ChangeCardViewTest(TestCase):

    def setUp(self):
        self.url = reverse("djstripe:change_card")
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com", password="password")
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
    def test_post_new_card(self, stripe_customer_create_mock, add_card_mock, send_invoice_mock, retry_unpaid_invoices_mock):
        self.client.post(self.url, {"stripe_token": "alpha"})
        add_card_mock.assert_called_once_with(self.user.customer, "alpha")
        send_invoice_mock.assert_called_with(self.user.customer)
        retry_unpaid_invoices_mock.assert_called_once_with(self.user.customer)

    # Needs to be refactored to use sources
    @patch("djstripe.models.Customer.retry_unpaid_invoices", autospec=True)
    @patch("djstripe.models.Customer.send_invoice", autospec=True)
    @patch("djstripe.models.Customer.add_card", autospec=True)
    def test_post_change_card(self, add_card_mock, send_invoice_mock, retry_unpaid_invoices_mock):
        customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        source = StripeSource.objects.create(customer=customer)
        customer.default_source = source
        customer.save()

        self.assertEqual(1, Customer.objects.count())

        self.client.post(self.url, {"stripe_token": "beta"})
        self.assertEqual(1, Customer.objects.count())
        add_card_mock.assert_called_once_with(self.user.customer, "beta")
        self.assertFalse(send_invoice_mock.called)
        retry_unpaid_invoices_mock.assert_called_once_with(self.user.customer)

    # Needs to be refactored to use sources
    @patch("djstripe.models.Customer.add_card", autospec=True)
    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_post_card_error(self, stripe_create_customer_mock, add_card_mock):
        add_card_mock.side_effect = StripeError("An error occurred while processing your card.")

        response = self.client.post(self.url, {"stripe_token": "pie"})
        add_card_mock.assert_called_once_with(self.user.customer, "pie")
        self.assertIn("stripe_error", response.context)
        self.assertIn("An error occurred while processing your card.", response.context["stripe_error"])

    # Needs to be refactored to use sources
    @patch("djstripe.models.Customer.add_card", autospec=True)
    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_post_no_card(self, stripe_create_customer_mock, add_card_mock):
        add_card_mock.side_effect = StripeError("Invalid source object:")

        response = self.client.post(self.url)
        add_card_mock.assert_called_once_with(self.user.customer, None)
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


class HistoryViewTest(TestCase):

    def setUp(self):
        self.url = reverse("djstripe:history")
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com", password="password")
        self.assertTrue(self.client.login(username="pydanny", password="password"))

    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_get_object(self, stripe_create_customer_mock):
        view_instance = HistoryView()
        request = RequestFactory()
        request.user = self.user

        view_instance.request = request
        object_a = view_instance.get_object()

        stripe_create_customer_mock.assert_called_once_with(api_key=settings.STRIPE_SECRET_KEY, email=self.user.email)

        customer_instance = Customer.objects.get(subscriber=self.user)
        self.assertEqual(customer_instance, object_a)


class SyncHistoryViewTest(TestCase):

    def setUp(self):
        self.url = reverse("djstripe:sync_history")
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com", password="password")
        self.assertTrue(self.client.login(username="pydanny", password="password"))

    @patch("djstripe.views.sync_subscriber", new_callable=PropertyMock, return_value=PropertyMock(subscriber="pie"))
    def test_post(self, sync_subscriber_mock):
        response = self.client.post(self.url)

        sync_subscriber_mock.assert_called_once_with(self.user)

        self.assertEqual("pie", response.context["customer"].subscriber)


class ConfirmFormViewTest(TestCase):

    def setUp(self):
        self.plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        self.url = reverse("djstripe:confirm", kwargs={"plan_id": self.plan.id})
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com", password="password")
        self.assertTrue(self.client.login(username="pydanny", password="password"))

    def test_get_form_current_plan(self):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        subscription = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=5)
        subscription.save()

        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("djstripe:subscribe"))

    def test_get_form_no_current_plan(self):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))

        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)

    def test_get_form_unknown_plan_id(self):
        response = self.client.get(reverse("djstripe:confirm", kwargs={'plan_id': (-1)}))
        self.assertEqual(404, response.status_code)

    @patch("djstripe.models.Customer.subscribe", autospec=True)
    @patch("djstripe.models.Customer.add_card", autospec=True)
    def test_post_valid(self, add_card_mock, subscribe_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

        self.assertEqual(1, Customer.objects.count())
        response = self.client.post(self.url, {"plan": self.plan.id, "stripe_token": "cake"})

        self.assertEqual(1, Customer.objects.count())
        add_card_mock.assert_called_once_with(self.user.customer, "cake")
        subscribe_mock.assert_called_once_with(self.user.customer, self.plan)

        self.assertRedirects(response, reverse("djstripe:history"))

    @patch("djstripe.models.Customer.subscribe", autospec=True)
    @patch("djstripe.models.Customer.add_card", autospec=True)
    def test_post_no_card(self, add_card_mock, subscribe_mock):
        add_card_mock.side_effect = StripeError("Invalid source object:")
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

        response = self.client.post(self.url, {"plan": self.plan.id})
        self.assertEqual(200, response.status_code)
        self.assertIn("form", response.context)
        self.assertIn("Invalid source object:", response.context["form"].errors["__all__"])

    def test_post_form_invalid(self):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

        response = self.client.post(self.url)
        self.assertEqual(200, response.status_code)
        self.assertIn("plan", response.context["form"].errors)
        self.assertIn("This field is required.", response.context["form"].errors["plan"])


class ChangePlanViewTest(TestCase):

    def setUp(self):
        self.url = reverse("djstripe:change_plan")
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com", password="password")
        self.assertTrue(self.client.login(username="pydanny", password="password"))

    def test_post_form_invalid(self):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))

        response = self.client.post(self.url)
        self.assertEqual(200, response.status_code)
        self.assertIn("plan", response.context["form"].errors)
        self.assertIn("This field is required.", response.context["form"].errors["plan"])

    def test_post_new_sub_no_proration(self):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        response = self.client.post(self.url)
        self.assertEqual(200, response.status_code)
        self.assertIn("form", response.context)
        self.assertIn("You must already be subscribed to a plan before you can change it.", response.context["form"].errors["__all__"])

    @patch("djstripe.models.Subscription.update", autospec=True)
    def test_change_sub_no_proration(self, subscription_update_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        subscription = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))

        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN_II))

        response = self.client.post(self.url, {"plan": plan.id})
        self.assertRedirects(response, reverse("djstripe:history"))

        subscription_update_mock.assert_called_once_with(subscription, plan=plan)

    @patch("djstripe.views.djstripe_settings.PRORATION_POLICY_FOR_UPGRADES", return_value=True)
    @patch("djstripe.models.Subscription.update", autospec=True)
    def test_change_sub_with_proration_downgrade(self, subscription_update_mock, proration_policy_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        subscription = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION_II))
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=5)
        subscription.save()

        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        response = self.client.post(self.url, {"plan": plan.id})
        self.assertRedirects(response, reverse("djstripe:history"))

        subscription_update_mock.assert_called_once_with(subscription, plan=plan)

    @patch("djstripe.views.djstripe_settings.PRORATION_POLICY_FOR_UPGRADES", return_value=True)
    @patch("djstripe.models.Subscription.update", autospec=True)
    def test_change_sub_with_proration_upgrade(self, subscription_update_mock, proration_policy_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        subscription = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=5)
        subscription.save()

        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN_II))

        response = self.client.post(self.url, {"plan": plan.id})
        self.assertRedirects(response, reverse("djstripe:history"))

        subscription_update_mock.assert_called_once_with(subscription, plan=plan, prorate=True)

    @patch("djstripe.views.djstripe_settings.PRORATION_POLICY_FOR_UPGRADES", return_value=True)
    @patch("djstripe.models.Subscription.update", autospec=True)
    def test_change_sub_with_proration_same_plan(self, subscription_update_mock, proration_policy_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        subscription = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=5)
        subscription.save()

        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        response = self.client.post(self.url, {"plan": plan.id})
        self.assertRedirects(response, reverse("djstripe:history"))

        subscription_update_mock.assert_called_once_with(subscription, plan=plan)

    @patch("djstripe.models.Subscription.update", autospec=True)
    def test_change_sub_same_plan(self, subscription_update_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        subscription = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=5)
        subscription.save()

        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        response = self.client.post(self.url, {"plan": plan.id})
        self.assertRedirects(response, reverse("djstripe:history"))

        subscription_update_mock.assert_called_once_with(subscription, plan=plan)

    @patch("djstripe.models.Subscription.update", autospec=True)
    def test_change_sub_stripe_error(self, subscription_update_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        subscription = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=5)
        subscription.save()

        error_string = "No such plan: {plan_id}".format(plan_id=FAKE_PLAN["id"])
        subscription_update_mock.side_effect = StripeError(error_string)

        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        response = self.client.post(self.url, {"plan": plan.id})
        self.assertEqual(200, response.status_code)
        self.assertIn("form", response.context)
        self.assertIn(error_string, response.context["form"].errors["__all__"])


class CancelSubscriptionViewTest(TestCase):
    def setUp(self):
        self.plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        self.url = reverse("djstripe:cancel_subscription")
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com", password="password")
        self.assertTrue(self.client.login(username="pydanny", password="password"))

    @patch("djstripe.models.Subscription.cancel")
    def test_cancel_proration(self, cancel_subscription_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        cancel_subscription_mock.return_value = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))

        response = self.client.post(self.url)

        cancel_subscription_mock.assert_called_once_with()
        self.assertRedirects(response, reverse("djstripe:account"))
        self.assertTrue(self.user.is_authenticated())

    @patch("djstripe.views.auth_logout", autospec=True)
    @patch("djstripe.models.Subscription.cancel")
    def test_cancel_no_proration(self, cancel_subscription_mock, logout_mock):
        Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION)
        fake_subscription.update({"status": Subscription.STATUS_CANCELED})
        cancel_subscription_mock.return_value = Subscription.sync_from_stripe_data(fake_subscription)

        response = self.client.post(self.url)

        cancel_subscription_mock.assert_called_once_with()
        self.assertEqual(response.status_code, 302)

        self.assertTrue(logout_mock.called)
