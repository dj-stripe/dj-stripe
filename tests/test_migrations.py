"""
dj-stripe Migrations Tests
"""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from djstripe.models.core import Customer
from djstripe.settings import djstripe_settings


class TestCustomerSubscriberFK(TestCase):
    @override_settings(
        DJSTRIPE_SUBSCRIBER_MODEL="testapp.Organization",
        DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK=(lambda request: request.org),
    )
    def setUp(self):
        return super().setUp()

    def test_customer_subscriber_fk_to_subscriber_model(self):
        """
        Test to ensure customer.subscriber fk points to the configured model
        set by DJSTRIPE_SUBSCRIBER_MODEL
        """
        field = Customer._meta.get_field("subscriber")

        self.assertEqual(field.related_model, djstripe_settings.get_subscriber_model())
        self.assertNotEqual(field.related_model, settings.AUTH_USER_MODEL)

    def test_customer_subscriber_fk_fallback_to_auth_user_model(self):
        """
        Test to ensure customer.subscriber fk points to the fallback AUTH_USER_MODEL
        when DJSTRIPE_SUBSCRIBER_MODEL is not set
        """
        # assert DJSTRIPE_SUBSCRIBER_MODEL has not been set
        with pytest.raises(AttributeError):
            settings.DJSTRIPE_SUBSCRIBER_MODEL

        field = Customer._meta.get_field("subscriber")
        self.assertEqual(field.related_model, get_user_model())
