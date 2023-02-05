"""
dj-stripe Product model tests
"""

from copy import deepcopy

import pytest
import stripe

from djstripe.models import Product
from djstripe.models.core import Price

from . import (
    FAKE_FILEUPLOAD_ICON,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_PRICE,
    FAKE_PRICE_METERED,
    FAKE_PRICE_ONETIME,
    FAKE_PRICE_TIER,
    FAKE_PRODUCT,
)

pytestmark = pytest.mark.django_db


class TestProduct:
    #
    # Helper Methods for monkeypatching
    #
    def mock_file_retrieve(*args, **kwargs):
        return deepcopy(FAKE_FILEUPLOAD_ICON)

    def mock_account_retrieve(*args, **kwargs):
        return deepcopy(FAKE_PLATFORM_ACCOUNT)

    def mock_product_get(self, *args, **kwargs):
        return deepcopy(FAKE_PRODUCT)

    @pytest.mark.parametrize("count", [1, 2, 3])
    def test___str__(self, count, monkeypatch):
        def mock_price_get(*args, **kwargs):
            return random_price_data

        # monkeypatch stripe.Product.retrieve and stripe.Price.retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Product, "retrieve", self.mock_product_get)
        monkeypatch.setattr(stripe.Price, "retrieve", mock_price_get)

        product = Product.sync_from_stripe_data(deepcopy(FAKE_PRODUCT))

        PRICE_DATA_OPTIONS = [
            deepcopy(FAKE_PRICE),
            deepcopy(FAKE_PRICE_TIER),
            deepcopy(FAKE_PRICE_METERED),
            deepcopy(FAKE_PRICE_ONETIME),
        ]
        for _ in range(count):
            random_price_data = PRICE_DATA_OPTIONS.pop()
            price = Price.sync_from_stripe_data(random_price_data)

        if count > 1:
            assert f"{FAKE_PRODUCT['name']} ({count} prices)" == str(product)
        else:
            assert f"{FAKE_PRODUCT['name']} ({price.human_readable_price})" == str(
                product
            )

    def test_sync_from_stripe_data(self, monkeypatch):
        # monkeypatch stripe.Product.retrieve call to return
        # the desired json response.
        monkeypatch.setattr(stripe.Product, "retrieve", self.mock_product_get)
        product = Product.sync_from_stripe_data(deepcopy(FAKE_PRODUCT))

        assert product.id == FAKE_PRODUCT["id"]
        assert product.name == FAKE_PRODUCT["name"]
        assert product.type == FAKE_PRODUCT["type"]
