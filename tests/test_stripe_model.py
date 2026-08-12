"""
dj-stripe StripeModel Model Tests.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase

from djstripe.models import (
    Account,
    APIKey,
    Coupon,
    Customer,
    Price,
    Product,
    StripeModel,
)
from djstripe.settings import djstripe_settings

from . import StripeList

pytestmark = pytest.mark.django_db


class ExampleStripeModel(StripeModel):
    # exists to avoid "Abstract models cannot be instantiated." error
    pass


class TestStripeModelExceptions(TestCase):
    def test_no_object_value(self):
        # Instantiate a stripeobject model class
        class BasicModel(StripeModel):
            pass

        with self.assertRaises(ValueError):
            # Errors because there's no object value
            BasicModel._stripe_object_to_record(
                {"id": "test_XXXXXXXX", "livemode": False}
            )

    def test_bad_object_value(self):
        with self.assertRaises(ValueError):
            # Errors because the object is not correct
            Customer._stripe_object_to_record(
                {"id": "test_XXXXXXXX", "livemode": False, "object": "not_a_customer"}
            )


@pytest.mark.parametrize("stripe_account", (None, "acct_fakefakefakefake001"))
@pytest.mark.parametrize(
    "api_key, expected_api_key",
    (
        (None, djstripe_settings.STRIPE_SECRET_KEY),
        ("sk_fakefakefake01", "sk_fakefakefake01"),
    ),
)
@pytest.mark.parametrize("extra_kwargs", ({}, {"foo": "bar"}))
@patch.object(target=StripeModel, attribute="stripe_class")
def test__api_delete(
    mock_stripe_class, stripe_account, api_key, expected_api_key, extra_kwargs
):
    """Test that API delete properly uses the passed in parameters."""
    test_model = ExampleStripeModel()
    mock_id = "id_fakefakefakefake01"
    test_model.id = mock_id

    # invoke _api_delete()
    test_model._api_delete(
        api_key=api_key, stripe_account=stripe_account, **extra_kwargs
    )

    mock_stripe_class.delete.assert_called_once_with(
        mock_id,
        api_key=expected_api_key,
        stripe_account=stripe_account,
        stripe_version=djstripe_settings.STRIPE_API_VERSION,
        **extra_kwargs,
    )


@pytest.mark.parametrize("stripe_account", (None, "acct_fakefakefakefake001"))
@pytest.mark.parametrize(
    "api_key, expected_api_key",
    (
        (None, djstripe_settings.STRIPE_SECRET_KEY),
        ("sk_fakefakefake01", "sk_fakefakefake01"),
    ),
)
@pytest.mark.parametrize("expand_fields", ([], ["foo", "bar"]))
@patch.object(target=StripeModel, attribute="stripe_class")
def test_api_retrieve(
    mock_stripe_class, stripe_account, api_key, expected_api_key, expand_fields
):
    """Test that API delete properly uses the passed in parameters."""
    test_model = ExampleStripeModel()
    mock_id = "id_fakefakefakefake01"
    test_model.id = mock_id
    test_model.expand_fields = expand_fields
    test_model.api_retrieve(api_key=api_key, stripe_account=stripe_account)

    mock_stripe_class.retrieve.assert_called_once_with(
        id=mock_id,
        api_key=expected_api_key,
        stripe_account=stripe_account,
        stripe_version=djstripe_settings.STRIPE_API_VERSION,
        expand=expand_fields,
    )


@patch.object(target=StripeModel, attribute="stripe_class")
def test_api_retrieve_reverse_foreign_key_lookup(mock_stripe_class):
    """Test that the reverse foreign key lookup finds the correct fields."""
    # Set up some mock fields that shouldn't be used for reverse lookups
    mock_field_1 = MagicMock()
    mock_field_1.is_relation = False
    mock_field_2 = MagicMock()
    mock_field_2.is_relation = True
    mock_field_2.one_to_many = False
    # Set up a mock reverse foreign key field
    mock_reverse_foreign_key = MagicMock()
    mock_reverse_foreign_key.is_relation = True
    mock_reverse_foreign_key.one_to_many = True
    mock_reverse_foreign_key.related_model = Account
    mock_reverse_foreign_key.get_accessor_name.return_value = "foo_account_reverse_attr"

    # Set up a mock account for the reverse foreign key query to return.
    mock_account = MagicMock()
    mock_account_reverse_manager = MagicMock()
    # Make first return the mock account.
    mock_account_reverse_manager.first.return_value = mock_account

    test_model = ExampleStripeModel()
    mock_id = "id_fakefakefakefake01"
    test_model.id = mock_id
    # Set mock reverse manager on the model.
    test_model.foo_account_reverse_attr = mock_account_reverse_manager

    # Set the mocked _meta.get_fields to return some mock fields, including the mock
    # reverse foreign key above.
    test_model._meta = MagicMock()
    test_model._meta.get_fields.return_value = (
        mock_field_1,
        mock_field_2,
        mock_reverse_foreign_key,
    )

    # Call the function with API key set because we mocked _meta
    mock_api_key = "sk_fakefakefakefake01"
    test_model.api_retrieve(api_key=mock_api_key)

    # Expect the retrieve to be done with the reverse look up of the Account ID.
    mock_stripe_class.retrieve.assert_called_once_with(
        id=mock_id,
        api_key=mock_api_key,
        stripe_account=mock_account.id,
        expand=[],
        stripe_version=djstripe_settings.STRIPE_API_VERSION,
    )
    mock_reverse_foreign_key.get_accessor_name.assert_called_once_with()
    mock_account_reverse_manager.first.assert_called_once_with()


@pytest.mark.parametrize("api_key", (None, "sk_fakefakefake01"))
@patch.object(target=Account, attribute="get_or_retrieve_for_api_key")
def test__find_owner_account_for_empty_data(
    mock_get_or_retrieve_for_api_key,
    api_key,
):
    """
    Test that the correct classmethod is invoked with the correct arguments
    to get the owner account
    """

    fake_data = {}

    if api_key is None:
        # invoke _find_owner_account without the api_key parameter
        StripeModel._find_owner_account(fake_data)
    else:
        # invoke _find_owner_account with the api_key parameter
        StripeModel._find_owner_account(fake_data, api_key=api_key)

    if api_key:
        mock_get_or_retrieve_for_api_key.assert_called_once_with(api_key)
    else:
        mock_get_or_retrieve_for_api_key.assert_called_once_with(
            djstripe_settings.STRIPE_SECRET_KEY
        )


@pytest.mark.parametrize(
    "has_stripe_account_attr,stripe_account",
    ((False, None), (True, ""), (True, "acct_fakefakefakefake001")),
)
@pytest.mark.parametrize("api_key", (None, "sk_fakefakefake01"))
@patch.object(target=Account, attribute="get_or_retrieve_for_api_key")
@patch.object(target=Account, attribute="_get_or_retrieve")
def test__find_owner_account(
    mock__get_or_retrieve,
    mock_get_or_retrieve_for_api_key,
    api_key,
    stripe_account,
    has_stripe_account_attr,
    monkeypatch,
):
    """
    Test that the correct classmethod is invoked with the correct arguments
    to get the owner account
    """

    # fake_data_class used to invoke _find_owner_account classmethod
    class fake_data_class:
        @property
        def stripe_account(self):
            return stripe_account

        def get(*args, **kwargs):
            return "customer"

    fake_data = fake_data_class()

    if api_key is None:
        # invoke _find_owner_account without the api_key parameter
        StripeModel._find_owner_account(fake_data)
    else:
        # invoke _find_owner_account with the api_key parameter
        StripeModel._find_owner_account(fake_data, api_key=api_key)

    if has_stripe_account_attr and stripe_account:
        if api_key:
            mock__get_or_retrieve.assert_called_once_with(
                id=stripe_account, api_key=api_key
            )
        else:
            mock__get_or_retrieve.assert_called_once_with(
                id=stripe_account, api_key=djstripe_settings.STRIPE_SECRET_KEY
            )

    else:
        if api_key:
            mock_get_or_retrieve_for_api_key.assert_called_once_with(api_key)
        else:
            mock_get_or_retrieve_for_api_key.assert_called_once_with(
                djstripe_settings.STRIPE_SECRET_KEY
            )


@pytest.mark.parametrize(
    "has_account_key,stripe_account",
    ((False, None), (True, ""), (True, "acct_fakefakefakefake001")),
)
@pytest.mark.parametrize("api_key", (None, "sk_fakefakefake01"))
@patch.object(target=Account, attribute="get_or_retrieve_for_api_key")
@patch.object(target=Account, attribute="_get_or_retrieve")
def test__find_owner_account_for_webhook_event_trigger(
    mock__get_or_retrieve,
    mock_get_or_retrieve_for_api_key,
    api_key,
    stripe_account,
    has_account_key,
):
    """
    Test that the correct classmethod is invoked with the correct arguments
    to get the owner account
    """

    # should fake_data have the account key
    if has_account_key:
        # fake_data used to invoke _find_owner_account classmethod
        fake_data = {
            "id": "test_XXXXXXXX",
            "livemode": False,
            "object": "event",
            "account": stripe_account,
        }
    else:
        # fake_data used to invoke _find_owner_account classmethod
        fake_data = {
            "id": "test_XXXXXXXX",
            "livemode": False,
            "object": "event",
        }

    if api_key is None:
        # invoke _find_owner_account without the api_key parameter
        StripeModel._find_owner_account(fake_data)
    else:
        # invoke _find_owner_account with the api_key parameter
        StripeModel._find_owner_account(fake_data, api_key=api_key)

    if has_account_key and stripe_account:
        if api_key:
            mock__get_or_retrieve.assert_called_once_with(
                id=stripe_account, api_key=api_key
            )
        else:
            mock__get_or_retrieve.assert_called_once_with(
                id=stripe_account, api_key=djstripe_settings.STRIPE_SECRET_KEY
            )

    else:
        if api_key:
            mock_get_or_retrieve_for_api_key.assert_called_once_with(api_key)
        else:
            mock_get_or_retrieve_for_api_key.assert_called_once_with(
                djstripe_settings.STRIPE_SECRET_KEY
            )


class TestSyncFromStripeData(TestCase):
    """Tests for `StripeModel.sync_from_stripe_data`."""

    def setUp(self):
        # Seed the owner account so syncing resolves it locally rather than
        # reaching for the Stripe API.
        account = Account.objects.create(
            id="acct_test_sync",
            stripe_data={"id": "acct_test_sync", "object": "account"},
        )
        key, _ = APIKey.objects.get_or_create_by_api_key(
            djstripe_settings.STRIPE_SECRET_KEY
        )
        key.djstripe_owner_account = account
        key.save()

    @staticmethod
    def _coupon_data(percent_off):
        return {
            "id": "co_test_sync",
            "object": "coupon",
            "duration": "forever",
            "percent_off": percent_off,
            "livemode": False,
            "valid": True,
            "metadata": {},
        }

    def test_updates_an_existing_instance(self):
        # Regression for #2032: syncing an object that already exists must
        # persist the new data, not just return the stale row.
        created = Coupon.sync_from_stripe_data(self._coupon_data(10))
        assert created.stripe_data["percent_off"] == 10

        returned = Coupon.sync_from_stripe_data(self._coupon_data(25))

        # The returned instance reflects the new data...
        assert returned.stripe_data["percent_off"] == 25
        # ...and so does a fresh read from the database.
        assert Coupon.objects.get(id="co_test_sync").stripe_data["percent_off"] == 25
        assert Coupon.objects.count() == 1

    @staticmethod
    def _product_data(id):
        return {
            "id": id,
            "object": "product",
            "active": True,
            "name": id,
            "livemode": False,
            "metadata": {},
        }

    def _price_data(self, product_id):
        return {
            "id": "price_test_sync",
            "object": "price",
            "active": True,
            "currency": "usd",
            "product": product_id,
            "unit_amount": 1000,
            "livemode": False,
            "metadata": {},
        }

    def test_updates_a_foreign_key_on_an_existing_instance(self):
        # Most sync tests write into an empty database, so the `not created`
        # branch's handling of relations is barely covered (#799).
        for product_id in ("prod_before", "prod_after"):
            Product.sync_from_stripe_data(self._product_data(product_id))

        Price.sync_from_stripe_data(self._price_data("prod_before"))
        Price.sync_from_stripe_data(self._price_data("prod_after"))

        price = Price.objects.get(id="price_test_sync")
        assert price.product_id is not None
        assert price.product.id == "prod_after"
        assert Price.objects.count() == 1

    def test_updates_a_foreign_key_given_a_nested_object(self):
        # Stripe may send the relation expanded rather than as a bare id.
        Product.sync_from_stripe_data(self._product_data("prod_before"))
        Price.sync_from_stripe_data(self._price_data("prod_before"))

        nested = self._price_data("prod_after")
        nested["product"] = self._product_data("prod_after")
        Price.sync_from_stripe_data(nested)

        price = Price.objects.get(id="price_test_sync")
        assert price.product.id == "prod_after"
        # The expanded object is synced too, not just linked by id.
        assert Product.objects.filter(id="prod_after").exists()

    @patch("stripe.Product.list_features", return_value=StripeList(data=[]))
    def test_an_expanded_relation_does_not_refresh_an_existing_row(
        self, list_features_mock
    ):
        """
        Documents current behaviour, which may not be intended.

        When a relation arrives expanded, the payload is only used if the
        target row is missing. `_get_or_create_from_stripe_object` returns the
        existing row at `base.py:758` before looking at the data, so a related
        object that changed in Stripe stays stale locally until it is synced in
        its own right.
        """
        Product.sync_from_stripe_data(self._product_data("prod_before"))
        Price.sync_from_stripe_data(self._price_data("prod_before"))

        renamed = self._price_data("prod_before")
        renamed["product"] = self._product_data("prod_before") | {"name": "renamed"}
        Price.sync_from_stripe_data(renamed)

        product = Product.objects.get(id="prod_before")
        assert product.stripe_data["name"] == "prod_before"  # not "renamed"

        # Syncing the product directly does apply the change, so the data is
        # reachable -- it is only the nested path that drops it.
        Product.sync_from_stripe_data(
            self._product_data("prod_before") | {"name": "renamed"}
        )
        product.refresh_from_db()
        assert product.stripe_data["name"] == "renamed"
