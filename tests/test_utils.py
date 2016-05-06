"""
.. module:: dj-stripe.tests.test_utils
   :synopsis: dj-stripe Utilities Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
from datetime import datetime
from unittest.case import SkipTest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from mock import patch

from djstripe.models import Customer, Subscription
from djstripe.utils import subscriber_has_active_subscription, get_supported_currency_choices, convert_tstamp
from tests import FAKE_SUBSCRIPTION, FAKE_CUSTOMER
from tests.apps.testapp.models import Organization


class TestTimestampConversion(TestCase):

    def test_conversion_without_field_name(self):
        stamp = convert_tstamp(1365567407)
        self.assertEquals(
            stamp,
            datetime(2013, 4, 10, 4, 16, 47, tzinfo=timezone.utc)
        )

    def test_conversion_with_field_name(self):
        stamp = convert_tstamp({"my_date": 1365567407}, "my_date")
        self.assertEquals(
            stamp,
            datetime(2013, 4, 10, 4, 16, 47, tzinfo=timezone.utc)
        )

    def test_conversion_with_invalid_field_name(self):
        stamp = convert_tstamp({"my_date": 1365567407}, "foo")
        self.assertEquals(
            stamp,
            None
        )

    # NOTE: These next two tests will fail if your system clock is not in UTC
    # Travis CI is, and coverage is good, so...

    @override_settings(USE_TZ=False)
    def test_conversion_without_field_name_no_tz(self):
        if settings.DJSTRIPE_TESTS_SKIP_UTC:
            raise SkipTest("UTC test skipped via command-line arg.")

        stamp = convert_tstamp(1365567407)
        self.assertEquals(
            stamp,
            datetime(2013, 4, 10, 4, 16, 47),
            "Is your system clock timezone in UTC? Change it, or run tests with '--skip-utc'."
        )

    @override_settings(USE_TZ=False)
    def test_conversion_with_field_name_no_tz(self):
        if settings.DJSTRIPE_TESTS_SKIP_UTC:
            raise SkipTest("UTC test skipped via command-line arg.")

        stamp = convert_tstamp({"my_date": 1365567407}, "my_date")
        self.assertEquals(
            stamp,
            datetime(2013, 4, 10, 4, 16, 47),
            "Is your system clock timezone in UTC? Change it, or run tests with '--skip-utc'."
        )

    @override_settings(USE_TZ=False)
    def test_conversion_with_invalid_field_name_no_tz(self):
        stamp = convert_tstamp({"my_date": 1365567407}, "foo")
        self.assertEquals(
            stamp,
            None,
        )


class TestUserHasActiveSubscription(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        self.customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

    def test_user_has_inactive_subscription(self):
        self.assertFalse(subscriber_has_active_subscription(self.user))

    def test_user_has_active_subscription(self):
        subscription = Subscription.sync_from_stripe_data(deepcopy(FAKE_SUBSCRIPTION))
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=10)
        subscription.save()

        # Assert that the customer's subscription is valid
        self.assertTrue(subscriber_has_active_subscription(self.user))

    def test_custom_subscriber(self):
        """
        ``subscriber_has_active_subscription`` attempts to create a customer object
        for the current user. This causes a ValueError in this test because the
        database has already been established with auth.User.
        """

        subscriber = Organization.objects.create(email="email@test.com")
        self.assertRaises(ValueError, subscriber_has_active_subscription, subscriber)

    def test_anonymous_user(self):
        """
        This needs to throw an ImproperlyConfigured error so the developer
        can be guided to properly protect the subscription content.
        """

        anon_user = AnonymousUser()

        with self.assertRaises(ImproperlyConfigured):
            subscriber_has_active_subscription(anon_user)

    def test_staff_user(self):
        self.user.is_staff = True
        self.user.save()

        self.assertTrue(subscriber_has_active_subscription(self.user))

    def test_superuser(self):
        self.user.is_superuser = True
        self.user.save()

        self.assertTrue(subscriber_has_active_subscription(self.user))


class TestGetSupportedCurrencyChoices(TestCase):

    @patch("stripe.CountrySpec.retrieve", return_value={"supported_payment_currencies": ["usd", "cad", "eur"]})
    @patch("stripe.Account.retrieve", return_value={"country": "US"})
    def test_get_choices(self, stripe_account_retrieve_mock, stripe_countryspec_retrieve_mock):
        # Simple test to test sure that at least one currency choice tuple is returned.

        currency_choices = get_supported_currency_choices(None)
        stripe_account_retrieve_mock.assert_called_once_with()
        stripe_countryspec_retrieve_mock.assert_called_once_with("US")
        self.assertGreaterEqual(len(currency_choices), 1, "Currency choices pull returned an empty list.")
        self.assertEqual(tuple, type(currency_choices[0]), "Currency choices are not tuples.")
        self.assertIn(("usd", "USD"), currency_choices, "USD not in currency choices.")
