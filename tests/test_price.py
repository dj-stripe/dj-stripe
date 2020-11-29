"""
dj-stripe Price model tests
"""
from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase

from djstripe.enums import PriceType, PriceUsageType
from djstripe.models import Price, Product
from djstripe.settings import STRIPE_SECRET_KEY

from . import (
    FAKE_PRICE,
    FAKE_PRICE_METERED,
    FAKE_PRICE_ONETIME,
    FAKE_PRICE_TIER,
    FAKE_PRODUCT,
    AssertStripeFksMixin,
)


class PriceCreateTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        with patch(
            "stripe.Product.retrieve",
            return_value=deepcopy(FAKE_PRODUCT),
            autospec=True,
        ):
            self.stripe_product = Product(id=FAKE_PRODUCT["id"]).api_retrieve()

    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch("stripe.Price.create", return_value=deepcopy(FAKE_PRICE), autospec=True)
    def test_create_from_product_id(self, price_create_mock, product_retrieve_mock):
        fake_price = deepcopy(FAKE_PRICE)
        fake_price["unit_amount"] /= 100
        assert isinstance(fake_price["product"], str)

        price = Price.create(**fake_price)

        expected_create_kwargs = deepcopy(FAKE_PRICE)
        expected_create_kwargs["api_key"] = STRIPE_SECRET_KEY

        price_create_mock.assert_called_once_with(**expected_create_kwargs)

        self.assert_fks(price, expected_blank_fks={"djstripe.Customer.coupon"})

    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch("stripe.Price.create", return_value=deepcopy(FAKE_PRICE), autospec=True)
    def test_create_from_stripe_product(self, price_create_mock, product_retrieve_mock):
        fake_price = deepcopy(FAKE_PRICE)
        fake_price["product"] = self.stripe_product
        fake_price["unit_amount"] /= 100
        assert isinstance(fake_price["product"], dict)

        price = Price.create(**fake_price)

        expected_create_kwargs = deepcopy(FAKE_PRICE)
        expected_create_kwargs["product"] = self.stripe_product

        price_create_mock.assert_called_once_with(
            api_key=STRIPE_SECRET_KEY, **expected_create_kwargs
        )

        self.assert_fks(price, expected_blank_fks={"djstripe.Customer.coupon"})

    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch("stripe.Price.create", return_value=deepcopy(FAKE_PRICE), autospec=True)
    def test_create_from_djstripe_product(
        self, price_create_mock, product_retrieve_mock
    ):
        fake_price = deepcopy(FAKE_PRICE)
        fake_price["product"] = Product.sync_from_stripe_data(self.stripe_product)
        fake_price["unit_amount"] /= 100
        assert isinstance(fake_price["product"], Product)

        price = Price.create(**fake_price)

        price_create_mock.assert_called_once_with(
            api_key=STRIPE_SECRET_KEY, **FAKE_PRICE
        )

        self.assert_fks(price, expected_blank_fks={"djstripe.Customer.coupon"})

    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch("stripe.Price.create", return_value=deepcopy(FAKE_PRICE), autospec=True)
    def test_create_with_metadata(self, price_create_mock, product_retrieve_mock):
        metadata = {"other_data": "more_data"}
        fake_price = deepcopy(FAKE_PRICE)
        fake_price["unit_amount"] /= 100
        fake_price["metadata"] = metadata
        assert isinstance(fake_price["product"], str)

        price = Price.create(**fake_price)

        expected_create_kwargs = deepcopy(FAKE_PRICE)
        expected_create_kwargs["metadata"] = metadata

        price_create_mock.assert_called_once_with(
            api_key=STRIPE_SECRET_KEY, **expected_create_kwargs
        )

        self.assert_fks(price, expected_blank_fks={"djstripe.Customer.coupon"})


class PriceTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        self.price_data = deepcopy(FAKE_PRICE)
        with patch(
            "stripe.Product.retrieve",
            return_value=deepcopy(FAKE_PRODUCT),
            autospec=True,
        ):
            self.price = Price.sync_from_stripe_data(self.price_data)

    def test_str(self):
        assert str(self.price) == self.price_data["nickname"]

    def test_price_name(self):
        price = Price(id="price_xxxx", nickname="Price Test")
        assert str(price) == "Price Test"
        price.nickname = ""
        assert str(price) == "price_xxxx"

    @patch("stripe.Price.retrieve", return_value=FAKE_PRICE, autospec=True)
    def test_stripe_price(self, price_retrieve_mock):
        stripe_price = self.price.api_retrieve()
        price_retrieve_mock.assert_called_once_with(
            id=self.price_data["id"],
            api_key=STRIPE_SECRET_KEY,
            expand=["tiers"],
            stripe_account=None,
        )
        price = Price.sync_from_stripe_data(stripe_price)

        self.assert_fks(price, expected_blank_fks={"djstripe.Customer.coupon"})

        assert price.human_readable_price == "$20.00 USD/month"

    @patch("stripe.Price.retrieve", autospec=True)
    def test_stripe_tier_price(self, price_retrieve_mock):
        price_data = deepcopy(FAKE_PRICE_TIER)
        price = Price.sync_from_stripe_data(price_data)
        assert price.id == price_data["id"]
        assert price.unit_amount is None
        assert price.tiers is not None

        self.assert_fks(price, expected_blank_fks={"djstripe.Customer.coupon"})

    @patch("stripe.Price.retrieve", autospec=True)
    def test_stripe_metered_price(self, price_retrieve_mock):
        price_data = deepcopy(FAKE_PRICE_METERED)
        price = Price.sync_from_stripe_data(price_data)
        assert price.id == price_data["id"]
        assert price.recurring["usage_type"] == PriceUsageType.metered
        assert price.unit_amount is not None

        self.assert_fks(price, expected_blank_fks={"djstripe.Customer.coupon"})

    @patch("stripe.Price.retrieve", autospec=True)
    def test_stripe_onetime_price(self, price_retrieve_mock):
        price_data = deepcopy(FAKE_PRICE_ONETIME)
        price = Price.sync_from_stripe_data(price_data)
        assert price.id == price_data["id"]
        assert price.unit_amount is not None
        assert not price.recurring
        assert price.type == PriceType.one_time

        self.assert_fks(price, expected_blank_fks={"djstripe.Customer.coupon"})


class HumanReadablePriceTest(TestCase):
    def setUp(self):
        product_data = deepcopy(FAKE_PRODUCT)
        self.stripe_product = Product.sync_from_stripe_data(product_data)

    def test_human_readable_one_time(self):
        price = Price.objects.create(
            id="price-test-one-time",
            active=True,
            unit_amount=2000,
            currency="usd",
            product=self.stripe_product,
        )
        assert price.human_readable_price == "$20.00 USD (one time)"

    def test_human_readable_free_usd_daily(self):
        price = Price.objects.create(
            id="price-test-free-usd-daily",
            active=True,
            unit_amount=0,
            currency="usd",
            product=self.stripe_product,
            recurring=dict(
                interval="day",
                interval_count=1,
            ),
        )
        assert price.human_readable_price == "$0.00 USD/day"

    def test_human_readable_10_usd_weekly(self):
        price = Price.objects.create(
            id="price-test-10-usd-weekly",
            active=True,
            unit_amount=1000,
            currency="usd",
            product=self.stripe_product,
            recurring=dict(
                interval="week",
                interval_count=1,
            ),
        )
        assert price.human_readable_price == "$10.00 USD/week"

    def test_human_readable_10_usd_2weeks(self):
        price = Price.objects.create(
            id="price-test-10-usd-2w",
            active=True,
            unit_amount=1000,
            currency="usd",
            product=self.stripe_product,
            recurring={
                "interval": "week",
                "interval_count": 2,
            },
        )
        assert price.human_readable_price == "$10.00 USD every 2 weeks"

    def test_human_readable_499_usd_monthly(self):
        price = Price.objects.create(
            id="price-test-499-usd-monthly",
            active=True,
            unit_amount=499,
            currency="usd",
            product=self.stripe_product,
            recurring=dict(
                interval="month",
                interval_count=1,
            ),
        )
        assert price.human_readable_price == "$4.99 USD/month"

    def test_human_readable_25_usd_6months(self):
        price = Price.objects.create(
            id="price-test-25-usd-6m",
            active=True,
            unit_amount=2500,
            currency="usd",
            product=self.stripe_product,
            recurring=dict(
                interval="month",
                interval_count=6,
            ),
        )
        assert price.human_readable_price == "$25.00 USD every 6 months"

    def test_human_readable_10_usd_yearly(self):
        price = Price.objects.create(
            id="price-test-10-usd-yearly",
            active=True,
            unit_amount=1000,
            currency="usd",
            product=self.stripe_product,
            recurring=dict(
                interval="year",
                interval_count=1,
            ),
        )
        assert price.human_readable_price == "$10.00 USD/year"
