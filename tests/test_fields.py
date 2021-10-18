"""
dj-stripe Custom Field Tests.
"""
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from django.test.testcases import TestCase
from django.test.utils import override_settings

from djstripe.fields import StripeDateTimeField, StripeDecimalCurrencyAmountField

pytestmark = pytest.mark.django_db


class TestStripeDecimalCurrencyAmountField:
    noval = StripeDecimalCurrencyAmountField(name="noval")

    def test_stripe_to_db_none_val(self):
        assert self.noval.stripe_to_db({"noval": None}) is None

    @pytest.mark.parametrize(
        "expected,inputted",
        [
            (Decimal("1"), Decimal("100")),
            (Decimal("1.5"), Decimal("150")),
            (Decimal("0"), Decimal("0")),
        ],
    )
    def test_stripe_to_db_decimal_val(self, expected, inputted):
        assert expected == self.noval.stripe_to_db({"noval": inputted})


@override_settings(USE_TZ=timezone.utc)
class TestStripeDateTimeField(TestCase):
    noval = StripeDateTimeField(name="noval")

    def test_stripe_to_db_none_val(self):
        self.assertEqual(None, self.noval.stripe_to_db({"noval": None}))

    def test_stripe_to_db_datetime_val(self):
        self.assertEqual(
            datetime(1997, 9, 18, 7, 48, 35, tzinfo=timezone.utc),
            self.noval.stripe_to_db({"noval": 874568915}),
        )
