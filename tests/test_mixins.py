"""
.. module:: dj-stripe.tests.test_mixins
   :synopsis: dj-stripe Mixin Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test.client import RequestFactory
from django.test.testcases import TestCase
from mock import patch

from djstripe.mixins import PaymentsContextMixin, SubscriptionMixin
from djstripe.models import Plan

from . import FAKE_CUSTOMER, FAKE_PLAN, FAKE_PLAN_II


class TestPaymentsContextMixin(TestCase):

    def test_get_context_data(self):
        from django.conf import settings

        class TestSuperView(object):
            def get_context_data(self):
                return {}

        class TestView(PaymentsContextMixin, TestSuperView):
            pass

        context = TestView().get_context_data()
        self.assertIn("STRIPE_PUBLIC_KEY", context, "STRIPE_PUBLIC_KEY missing from context.")
        self.assertEqual(context["STRIPE_PUBLIC_KEY"], settings.STRIPE_PUBLIC_KEY, "Incorrect STRIPE_PUBLIC_KEY.")

        self.assertIn("plans", context, "pans missing from context.")
        self.assertEqual(list(Plan.objects.all()), list(context["plans"]), "Incorrect plans.")


class TestSubscriptionMixin(TestCase):

    def setUp(self):
        Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN_II))

    @patch("stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER))
    def test_get_context_data(self, stripe_create_customer_mock):

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
