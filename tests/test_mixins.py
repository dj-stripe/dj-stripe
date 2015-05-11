"""
.. module:: dj-stripe.tests.test_mixins
   :synopsis: dj-stripe Mixin Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.http.request import HttpRequest
from django.test.testcases import TestCase

from djstripe.mixins import SubscriptionPaymentRequiredMixin, PaymentsContextMixin, SubscriptionMixin
from django.test.client import RequestFactory


class TestSubscriptionPaymentRequiredMixin(TestCase):

    def setUp(self):
        self.request = HttpRequest()
        self.user = get_user_model().objects.create(username="x", email="user@test.com")
        self.superuser = get_user_model().objects.create(username="y", email="superuser@test.com", is_superuser=True)

    def test_dispatch_inactive_subscription(self):
        self.request.user = self.user

        mixin = SubscriptionPaymentRequiredMixin()
        response = mixin.dispatch(self.request)

        self.assertEqual(response.url, reverse("djstripe:subscribe"))

    def test_dispatch_active_subscription(self):
        self.request.user = self.superuser

        mixin = SubscriptionPaymentRequiredMixin()
        self.assertRaises(AttributeError, mixin.dispatch, self.request)


class TestPaymentsContextMixin(TestCase):

    def test_get_context_data(self):
        from django.conf import settings
        from djstripe import settings as djstripe_settings

        class TestSuperView(object):
            def get_context_data(self):
                return {}

        class TestView(PaymentsContextMixin, TestSuperView):
            pass

        context = TestView().get_context_data()
        self.assertIn("STRIPE_PUBLIC_KEY", context, "STRIPE_PUBLIC_KEY missing from context.")
        self.assertEqual(context["STRIPE_PUBLIC_KEY"], settings.STRIPE_PUBLIC_KEY, "Incorrect STRIPE_PUBLIC_KEY.")

        self.assertIn("PLAN_CHOICES", context, "PLAN_CHOICES missing from context.")
        self.assertEqual(context["PLAN_CHOICES"], djstripe_settings.PLAN_CHOICES, "Incorrect PLAN_CHOICES.")

        self.assertIn("PLAN_LIST", context, "PLAN_LIST missing from context.")
        self.assertEqual(context["PLAN_LIST"], djstripe_settings.PLAN_LIST, "Incorrect PLAN_LIST.")

        self.assertIn("PAYMENT_PLANS", context, "PAYMENT_PLANS missing from context.")
        self.assertEqual(context["PAYMENT_PLANS"], djstripe_settings.PAYMENT_PLANS, "Incorrect PAYMENT_PLANS.")


class TestSubscriptionMixin(TestCase):

    def test_get_context_data(self):

        class TestSuperView(object):
            def get_context_data(self):
                return {}

        class TestView(SubscriptionMixin, TestSuperView):
            pass

        test_view = TestView()

        test_view.request = RequestFactory()
        test_view.request.user = get_user_model().objects.create(username="x", email="user@test.com")

        context = test_view.get_context_data()
        self.assertIn("is_plans_plural", context, "is_plans_plural missing from context.")
        self.assertTrue(context["is_plans_plural"], "Incorrect is_plans_plural.")

        self.assertIn("customer", context, "customer missing from context.")

        self.assertIn("CurrentSubscription", context, "CurrentSubscription missing from context.")
