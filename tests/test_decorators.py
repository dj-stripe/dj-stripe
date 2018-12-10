"""
dj-stripe Decorator Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory

from djstripe.decorators import subscription_payment_required
from djstripe.models import Subscription

from . import FAKE_CUSTOMER, FAKE_PLAN, FAKE_SUBSCRIPTION, FUTURE_DATE


class TestSubscriptionPaymentRequired(TestCase):
	def setUp(self):
		self.settings(ROOT_URLCONF="tests.urls")
		self.factory = RequestFactory()

		@subscription_payment_required
		def test_view(request):
			return HttpResponse()

		self.test_view = test_view

	def test_direct(self):
		subscription_payment_required(function=None)

	def test_anonymous(self):
		request = self.factory.get("/account/")
		request.user = AnonymousUser()

		with self.assertRaises(ImproperlyConfigured):
			self.test_view(request)

	def test_user_unpaid(self):
		user = get_user_model().objects.create_user(
			username="pydanny", email="pydanny@gmail.com"
		)
		FAKE_CUSTOMER.create_for_user(user)

		request = self.factory.get("/account/")
		request.user = user

		response = self.test_view(request)
		self.assertEqual(response.status_code, 302)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	def test_user_active_subscription(self, plan_retrieve_mock):
		user = get_user_model().objects.create_user(
			username="pydanny", email="pydanny@gmail.com"
		)
		FAKE_CUSTOMER.create_for_user(user)
		subscription = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))
		subscription.current_period_end = FUTURE_DATE
		subscription.save()

		request = self.factory.get("/account/")
		request.user = user

		response = self.test_view(request)
		self.assertEqual(response.status_code, 200)
