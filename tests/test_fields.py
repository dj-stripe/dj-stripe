"""
dj-stripe Custom Field Tests.
"""
from datetime import datetime
from decimal import Decimal

import pytest
from django.test.testcases import TestCase
from django.test.utils import override_settings

from djstripe.fields import StripeDateTimeField, StripeDecimalCurrencyAmountField
from djstripe.utils import get_timezone_utc
from tests.fields.models import ExampleDecimalModel

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


@override_settings(USE_TZ=get_timezone_utc())
class TestStripeDateTimeField(TestCase):
    noval = StripeDateTimeField(name="noval")

    def test_stripe_to_db_none_val(self):
        self.assertEqual(None, self.noval.stripe_to_db({"noval": None}))

    def test_stripe_to_db_datetime_val(self):
        self.assertEqual(
            datetime(1997, 9, 18, 7, 48, 35, tzinfo=get_timezone_utc()),
            self.noval.stripe_to_db({"noval": 874568915}),
        )


class TestStripePercentField:
    @pytest.mark.parametrize(
        "inputted,expected",
        [
            (Decimal("1"), Decimal("1.00")),
            (Decimal("1.5234567"), Decimal("1.52")),
            (Decimal("0"), Decimal("0.00")),
            (Decimal("23.2345678"), Decimal("23.23")),
            ("1", Decimal("1.00")),
            ("1.5234567", Decimal("1.52")),
            ("0", Decimal("0.00")),
            ("23.2345678", Decimal("23.23")),
            (1, Decimal("1.00")),
            (1.5234567, Decimal("1.52")),
            (0, Decimal("0.00")),
            (23.2345678, Decimal("23.24")),
        ],
    )
    def test_stripe_percent_field(self, inputted, expected):
        # create a model with the StripePercentField
        model_field = ExampleDecimalModel(noval=inputted)
        model_field.save()

        # get the field data
        field_data = ExampleDecimalModel.objects.get(pk=model_field.pk).noval

        assert isinstance(field_data, Decimal)
        assert field_data == expected
