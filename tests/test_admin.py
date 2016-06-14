"""
.. module:: dj-stripe.tests.test_admin
   :synopsis: dj-stripe Admin Tests.

.. moduleauthor:: Oleksandr (@nanvel)

"""

from copy import deepcopy

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from mock import patch
import six

from djstripe.admin import subscription_status
from djstripe.models import Customer, Subscription
from tests import FAKE_CUSTOMER, FAKE_PLAN, FAKE_SUBSCRIPTION


class TestAdminSite(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")

    def test_search_fields(self):
        """
        Search for errors like this:
        Bad search field <customer__user__username> for Customer model.
        """

        for _model, model_admin in six.iteritems(admin.site._registry):
            for search_field in getattr(model_admin, 'search_fields', []):
                model_name = model_admin.model.__name__
                self.assertFalse(search_field.startswith('{table_name}__'.format(
                    table_name=model_name.lower())),
                    'Bad search field <{search_field}> for {model_name} model.'.format(
                        search_field=search_field, model_name=model_name))

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_subscription_status(self, customer_mock, plan_mock):
        customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        self.assertEqual(subscription.status, subscription_status(customer))

    def test_subscription_status_no_sub(self):
        customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

        self.assertEqual("", subscription_status(customer))
