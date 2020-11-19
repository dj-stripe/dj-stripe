"""
dj-stripe Utilities Tests.
"""
import time
from datetime import datetime
from decimal import Decimal
from unittest import skipIf
from unittest.mock import patch

from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from djstripe.utils import (
    convert_tstamp,
    get_friendly_currency_amount,
    get_supported_currency_choices,
)

from . import IS_STATICMETHOD_AUTOSPEC_SUPPORTED

TZ_IS_UTC = time.tzname == ("UTC", "UTC")


class TestTimestampConversion(TestCase):
    def test_conversion(self):
        stamp = convert_tstamp(1365567407)
        self.assertEqual(stamp, datetime(2013, 4, 10, 4, 16, 47, tzinfo=timezone.utc))

    # NOTE: These next two tests will fail if your system clock is not in UTC
    # Travis CI is, and coverage is good, so...

    @skipIf(not TZ_IS_UTC, "Skipped because timezone is not UTC.")
    @override_settings(USE_TZ=False)
    def test_conversion_no_tz(self):
        stamp = convert_tstamp(1365567407)
        self.assertEqual(stamp, datetime(2013, 4, 10, 4, 16, 47))


class TestGetSupportedCurrencyChoices(TestCase):
    @patch(
        "stripe.CountrySpec.retrieve",
        return_value={"supported_payment_currencies": ["usd", "cad", "eur"]},
    )
    @patch(
        "stripe.Account.retrieve",
        return_value={"country": "US"},
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    def test_get_choices(
        self, stripe_account_retrieve_mock, stripe_countryspec_retrieve_mock
    ):
        # Simple test to test sure that at least one currency choice tuple is returned.

        currency_choices = get_supported_currency_choices(None)
        stripe_account_retrieve_mock.assert_called_once_with()
        stripe_countryspec_retrieve_mock.assert_called_once_with("US")
        self.assertGreaterEqual(
            len(currency_choices), 1, "Currency choices pull returned an empty list."
        )
        self.assertEqual(
            tuple, type(currency_choices[0]), "Currency choices are not tuples."
        )
        self.assertIn(("usd", "USD"), currency_choices, "USD not in currency choices.")


class TestUtils(TestCase):
    def test_get_friendly_currency_amount(self):
        self.assertEqual(
            get_friendly_currency_amount(Decimal("1.001"), "usd"), "$1.00 USD"
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "usd"), "$10.00 USD"
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10.50"), "usd"), "$10.50 USD"
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10.51"), "cad"), "$10.51 CAD"
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("9.99"), "eur"), "€9.99 EUR"
        )
