"""
dj-stripe Mixin Tests.
"""

from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test.client import RequestFactory
from django.test.testcases import TestCase

from djstripe.mixins import PaymentsContextMixin, SubscriptionMixin
from djstripe.models import Price
from djstripe.settings import djstripe_settings

from . import FAKE_CUSTOMER, FAKE_PRICE, FAKE_PRICE_II, FAKE_PRODUCT
from .conftest import CreateAccountMixin


class TestPaymentsContextMixin(TestCase):
    def test_get_context_data(self):
        class TestSuperView:
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
            djstripe_settings.STRIPE_PUBLIC_KEY,
            "Incorrect STRIPE_PUBLIC_KEY.",
        )

        self.assertIn("prices", context, "prices missing from context.")
        self.assertEqual(
            list(Price.objects.all()), list(context["prices"]), "Incorrect prices."
        )


class TestSubscriptionMixin(CreateAccountMixin, TestCase):
    def setUp(self):
        with patch(
            "stripe.Product.retrieve",
            return_value=deepcopy(FAKE_PRODUCT),
            autospec=True,
        ):
            Price.sync_from_stripe_data(deepcopy(FAKE_PRICE))
            Price.sync_from_stripe_data(deepcopy(FAKE_PRICE_II))

    @patch(
        "stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_get_context_data(self, stripe_create_customer_mock):
        class TestSuperView:
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
            "is_prices_plural", context, "is_prices_plural missing from context."
        )
        self.assertTrue(context["is_prices_plural"], "Incorrect is_prices_plural.")

        self.assertIn("customer", context, "customer missing from context.")
