"""
dj-stripe Mixin Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test.client import RequestFactory
from django.test.testcases import TestCase

from djstripe.mixins import PaymentsContextMixin, SubscriptionMixin
from djstripe.models import Plan
from djstripe.settings import STRIPE_PUBLIC_KEY

from . import FAKE_CUSTOMER, FAKE_PLAN, FAKE_PLAN_II, FAKE_PRODUCT


class TestPaymentsContextMixin(TestCase):
    def test_get_context_data(self):
        class TestSuperView(object):
            def get_context_data(self):
                return {}

        class TestView(PaymentsContextMixin, TestSuperView):
            pass

        context = TestView().get_context_data()
        self.assertIn(
            "STRIPE_PUBLIC_KEY", context, "STRIPE_PUBLIC_KEY missing from context."
        )
        self.assertEqual(
            context["STRIPE_PUBLIC_KEY"],
            STRIPE_PUBLIC_KEY,
            "Incorrect STRIPE_PUBLIC_KEY.",
        )

        self.assertIn("plans", context, "pans missing from context.")
        self.assertEqual(
            list(Plan.objects.all()), list(context["plans"]), "Incorrect plans."
        )


class TestSubscriptionMixin(TestCase):
    def setUp(self):
        with patch(
            "stripe.Product.retrieve",
            return_value=deepcopy(FAKE_PRODUCT),
            autospec=True,
        ):
            Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
            Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN_II))

    @patch(
        "stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_get_context_data(self, stripe_create_customer_mock):
        class TestSuperView(object):
            def get_context_data(self):
                return {}

        class TestView(SubscriptionMixin, TestSuperView):
            pass

        test_view = TestView()

        test_view.request = RequestFactory()
        test_view.request.user = get_user_model().objects.create(
            username="x", email="user@test.com"
        )

        context = test_view.get_context_data()
        self.assertIn(
            "is_plans_plural", context, "is_plans_plural missing from context."
        )
        self.assertTrue(context["is_plans_plural"], "Incorrect is_plans_plural.")

        self.assertIn("customer", context, "customer missing from context.")
