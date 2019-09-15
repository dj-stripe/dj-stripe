"""
dj-stripe StripeModel Model Tests.
"""
from unittest.mock import MagicMock, call, patch

import pytest
from django.test import TestCase

from djstripe.models import Account, Customer, StripeModel
from djstripe.settings import STRIPE_SECRET_KEY


class StripeModelExceptionsTest(TestCase):
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
    ((None, STRIPE_SECRET_KEY), ("sk_fakefakefake01", "sk_fakefakefake01")),
)
@pytest.mark.parametrize("extra_kwargs", ({}, {"foo": "bar"}))
@patch.object(target=StripeModel, attribute="api_retrieve", autospec=True)
def test__api_delete(
    mock_api_retrieve, stripe_account, api_key, expected_api_key, extra_kwargs
):
    """Test that API delete properly uses the passed in parameters."""
    test_model = StripeModel()
    test_model._api_delete(
        api_key=api_key, stripe_account=stripe_account, **extra_kwargs
    )

    # Assert the chained calls happened as expected, since it should
    # call api_retrieve() followed by delete()
    assert (
        mock_api_retrieve.mock_calls
        == call(test_model, api_key=expected_api_key, stripe_account=stripe_account)
        .delete(**extra_kwargs)
        .call_list()
    )


@pytest.mark.parametrize("stripe_account", (None, "acct_fakefakefakefake001"))
@pytest.mark.parametrize(
    "api_key, expected_api_key",
    ((None, STRIPE_SECRET_KEY), ("sk_fakefakefake01", "sk_fakefakefake01")),
)
@pytest.mark.parametrize("expand_fields", ([], ["foo", "bar"]))
@patch.object(target=StripeModel, attribute="stripe_class")
def test_api_retrieve(
    mock_stripe_class, stripe_account, api_key, expected_api_key, expand_fields
):
    """Test that API delete properly uses the passed in parameters."""
    test_model = StripeModel()
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


@patch.object(target=StripeModel, attribute="_meta", autospec=True)
@patch.object(target=StripeModel, attribute="stripe_class")
def test_api_retrieve_reverse_foreign_key_lookup(mock_stripe_class, mock__meta):
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
    # Set the mocked _meta.get_fields to return some mock fields, including the mock
    # reverse foreign key above.
    mock__meta.get_fields.return_value = (
        mock_field_1,
        mock_field_2,
        mock_reverse_foreign_key,
    )
    # Set up a mock account for the reverse foreign key query to return.
    mock_account = MagicMock()
    mock_account_reverse_manager = MagicMock()
    # Make first return the mock account.
    mock_account_reverse_manager.first.return_value = mock_account

    test_model = StripeModel()
    mock_id = "id_fakefakefakefake01"
    test_model.id = mock_id
    # Set mock reverse manager on the model.
    test_model.foo_account_reverse_attr = mock_account_reverse_manager

    # Call the function with API key set because we mocked _meta
    mock_api_key = "sk_fakefakefakefake01"
    test_model.api_retrieve(api_key=mock_api_key)

    # Expect the retrieve to be done with the reverse look up of the Account ID.
    mock_stripe_class.retrieve.assert_called_once_with(
        id=mock_id, api_key=mock_api_key, stripe_account=mock_account.id, expand=[]
    )
    mock_reverse_foreign_key.get_accessor_name.assert_called_once_with()
    mock_account_reverse_manager.first.assert_called_once_with()
