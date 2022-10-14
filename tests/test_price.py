"""
dj-stripe Price model tests
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
import stripe
from django.test import TestCase

from djstripe.enums import PriceType, PriceUsageType
from djstripe.models import Price, Product, Subscription
from djstripe.settings import djstripe_settings

from . import (
    FAKE_PRICE,
    FAKE_PRICE_METERED,
    FAKE_PRICE_ONETIME,
    FAKE_PRICE_TIER,
    FAKE_PRODUCT,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


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
        expected_create_kwargs["api_key"] = djstripe_settings.STRIPE_SECRET_KEY

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
            api_key=djstripe_settings.STRIPE_SECRET_KEY, **expected_create_kwargs
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
            api_key=djstripe_settings.STRIPE_SECRET_KEY, **FAKE_PRICE
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
            api_key=djstripe_settings.STRIPE_SECRET_KEY, **expected_create_kwargs
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

    @patch("stripe.Price.retrieve", return_value=FAKE_PRICE, autospec=True)
    def test_stripe_price(self, price_retrieve_mock):
        stripe_price = self.price.api_retrieve()
        price_retrieve_mock.assert_called_once_with(
            id=self.price_data["id"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            expand=["product", "tiers"],
            stripe_account=self.price.djstripe_owner_account.id,
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


class TestStrPrice:
    @pytest.mark.parametrize(
        "fake_price_data",
        [
            deepcopy(FAKE_PRICE),
            deepcopy(FAKE_PRICE_ONETIME),
            deepcopy(FAKE_PRICE_TIER),
            deepcopy(FAKE_PRICE_METERED),
        ],
    )
    def test___str__(self, fake_price_data, monkeypatch):
        def mock_product_get(*args, **kwargs):
            return deepcopy(FAKE_PRODUCT)

        def mock_price_get(*args, **kwargs):
            return fake_price_data

        # monkeypatch stripe.Product.retrieve and stripe.Price.retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Product, "retrieve", mock_product_get)
        monkeypatch.setattr(stripe.Price, "retrieve", mock_price_get)

        if not fake_price_data["recurring"]:
            price = Price.sync_from_stripe_data(fake_price_data)
            assert (f"{price.human_readable_price} for {FAKE_PRODUCT['name']}") == str(
                price
            )

        else:
            price = Price.sync_from_stripe_data(fake_price_data)
            assert (
                str(price) == f"{price.human_readable_price} for {FAKE_PRODUCT['name']}"
            )


class TestHumanReadablePrice:

    #
    # Helpers
    #
    def get_fake_price_NONE_flat_amount():
        FAKE_PRICE_TIER_NONE_FLAT_AMOUNT = deepcopy(FAKE_PRICE_TIER)
        FAKE_PRICE_TIER_NONE_FLAT_AMOUNT["tiers"][0]["flat_amount"] = None
        FAKE_PRICE_TIER_NONE_FLAT_AMOUNT["tiers"][0]["flat_amount_decimal"] = None
        return FAKE_PRICE_TIER_NONE_FLAT_AMOUNT

    def get_fake_price_0_flat_amount():
        FAKE_PRICE_TIER_0_FLAT_AMOUNT = deepcopy(FAKE_PRICE_TIER)
        FAKE_PRICE_TIER_0_FLAT_AMOUNT["tiers"][0]["flat_amount"] = 0
        FAKE_PRICE_TIER_0_FLAT_AMOUNT["tiers"][0]["flat_amount_decimal"] = 0
        return FAKE_PRICE_TIER_0_FLAT_AMOUNT

    def get_fake_price_0_amount():
        FAKE_PRICE_TIER_0_AMOUNT = deepcopy(FAKE_PRICE)
        FAKE_PRICE_TIER_0_AMOUNT["unit_amount"] = 0
        FAKE_PRICE_TIER_0_AMOUNT["unit_amount_decimal"] = 0
        return FAKE_PRICE_TIER_0_AMOUNT

    @pytest.mark.parametrize(
        "fake_price_data, expected_str",
        [
            (deepcopy(FAKE_PRICE), "$20.00 USD/month"),
            (get_fake_price_0_amount(), "$0.00 USD/month"),
            (deepcopy(FAKE_PRICE_ONETIME), "$20.00 USD (one time)"),
            (
                deepcopy(FAKE_PRICE_TIER),
                "Starts at $10.00 USD per unit + $49.00 USD/month",
            ),
            (
                get_fake_price_0_flat_amount(),
                "Starts at $10.00 USD per unit + $0.00 USD/month",
            ),
            (
                get_fake_price_NONE_flat_amount(),
                "Starts at $10.00 USD per unit/month",
            ),
            (deepcopy(FAKE_PRICE_METERED), "$2.00 USD/month"),
        ],
    )
    def test_human_readable(self, fake_price_data, expected_str, monkeypatch):
        def mock_product_get(*args, **kwargs):
            return deepcopy(FAKE_PRODUCT)

        def mock_price_get(*args, **kwargs):
            return fake_price_data

        # monkeypatch stripe.Product.retrieve and stripe.Price.retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Product, "retrieve", mock_product_get)
        monkeypatch.setattr(stripe.Price, "retrieve", mock_price_get)

        price = Price.sync_from_stripe_data(fake_price_data)

        assert price.human_readable_price == expected_str
