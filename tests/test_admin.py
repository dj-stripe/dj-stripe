"""
.. module:: dj-stripe.tests.test_admin
   :synopsis: dj-stripe Admin Tests.

.. moduleauthor:: Oleksandr (@nanvel)
.. moduleauthor:: Lee Skillen (@lskillen)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from copy import deepcopy

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from mock import patch

from djstripe.admin import subscription_status
from djstripe.models import Subscription

from . import FAKE_CUSTOMER, FAKE_PLAN, FAKE_SUBSCRIPTION


class TestAdminSite(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")

    def test_search_fields(self):
        """
        Search for errors like this:
        Bad search field <customer__user__username> for Customer model.
        """

        for _model, model_admin in admin.site._registry.items():
            for search_field in getattr(model_admin, 'search_fields', []):
                model_name = model_admin.model.__name__
                self.assertFalse(search_field.startswith('{table_name}__'.format(
                    table_name=model_name.lower())),
                    'Bad search field <{search_field}> for {model_name} model.'.format(
                        search_field=search_field, model_name=model_name))

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_subscription_status(self, customer_mock, plan_mock):
        customer = FAKE_CUSTOMER.create_for_user(self.user)
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        self.assertEqual(subscription.status, subscription_status(customer))

    def test_subscription_status_no_sub(self):
        customer = FAKE_CUSTOMER.create_for_user(self.user)
        self.assertEqual("", subscription_status(customer))
