"""
dj-stripe StripeModel Model Tests.
"""
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase

from djstripe.models import Account, Customer, StripeModel
from djstripe.settings import djstripe_settings

pytestmark = pytest.mark.django_db


class TestStripeModel(StripeModel):
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
    test_model = TestStripeModel()
    mock_id = "id_fakefakefakefake01"
    test_model.id = mock_id

    # invoke _api_delete()
    test_model._api_delete(
        api_key=api_key, stripe_account=stripe_account, **extra_kwargs
    )

    mock_stripe_class.delete.assert_called_once_with(
        mock_id, api_key=expected_api_key, stripe_account=stripe_account, **extra_kwargs
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
    test_model = TestStripeModel()
    mock_id = "id_fakefakefakefake01"
    test_model.id = mock_id
    test_model.expand_fields = expand_fields
    test_model.api_retrieve(api_key=api_key, stripe_account=stripe_account)

    mock_stripe_class.retrieve.assert_called_once_with(
        id=mock_id,
        api_key=expected_api_key,
        stripe_account=stripe_account,
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

    test_model = TestStripeModel()
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
        id=mock_id, api_key=mock_api_key, stripe_account=mock_account.id, expand=[]
    )
    mock_reverse_foreign_key.get_accessor_name.assert_called_once_with()
    mock_account_reverse_manager.first.assert_called_once_with()


@pytest.mark.parametrize("stripe_account", (None, "acct_fakefakefakefake001"))
@pytest.mark.parametrize("api_key", (None, "sk_fakefakefake01"))
@patch.object(target=Account, attribute="get_or_retrieve_for_api_key")
@patch.object(target=Account, attribute="_get_or_retrieve")
def test__find_owner_account(
    mock__get_or_retrieve, mock_get_or_retrieve_for_api_key, stripe_account, api_key
):
    """
    Test that the correct classmethod is invoked with the correct arguments
    to get the owner account
    """
    # fake_data used to invoke _find_owner_account classmethod
    fake_data = {
        "id": "test_XXXXXXXX",
        "livemode": False,
        "object": "customer",
        "account": stripe_account,
    }

    if api_key is None:
        # invoke _find_owner_account without the api_key parameter
        StripeModel._find_owner_account(fake_data)
    else:
        # invoke _find_owner_account with the api_key parameter
        StripeModel._find_owner_account(fake_data, api_key=api_key)

    # if stripe_account exists, assert _get_or_retrieve classmethod
    # gets called
    if stripe_account:
        mock__get_or_retrieve.assert_called_once_with(id=stripe_account)

    # if api_key exists and stripe_account doesn't, assert get_or_retrieve_for_api_key
    # classmethod gets called
    if api_key and not stripe_account:
        mock_get_or_retrieve_for_api_key.assert_called_once_with(api_key)
