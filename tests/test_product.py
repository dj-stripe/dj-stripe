"""
dj-stripe Product model tests
"""

from copy import deepcopy

import pytest
import stripe

from djstripe.models import Product

from . import (
    FAKE_FILEUPLOAD_ICON,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_PRODUCT,
)
from .conftest import CreateAccountMixin

pytestmark = pytest.mark.django_db


class TestProduct(CreateAccountMixin):
    #
    # Helper Methods for monkeypatching
    #
    def mock_file_retrieve(*args, **kwargs):
        return deepcopy(FAKE_FILEUPLOAD_ICON)

    def mock_account_retrieve(*args, **kwargs):
        return deepcopy(FAKE_PLATFORM_ACCOUNT)

    def mock_product_get(self, *args, **kwargs):
        return deepcopy(FAKE_PRODUCT)

    def test___str__(self, monkeypatch):
        # Product.__str__ now returns just the product name; price-count
        # decoration was removed.
        monkeypatch.setattr(stripe.Product, "retrieve", self.mock_product_get)
        product = Product.sync_from_stripe_data(deepcopy(FAKE_PRODUCT))
        assert str(product) == FAKE_PRODUCT["name"]

    def test_sync_from_stripe_data(self, monkeypatch):
        # monkeypatch stripe.Product.retrieve call to return
        # the desired json response.
        monkeypatch.setattr(stripe.Product, "retrieve", self.mock_product_get)
        product = Product.sync_from_stripe_data(deepcopy(FAKE_PRODUCT))

        assert product.id == FAKE_PRODUCT["id"]
        assert product.name == FAKE_PRODUCT["name"]
        assert product.type == FAKE_PRODUCT["type"]
