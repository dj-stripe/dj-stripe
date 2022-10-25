"""
Module for creating re-usable fixtures to be used across the test suite
"""
import pytest
import stripe
from django.contrib.auth import get_user_model

from . import FAKE_CUSTOMER, FAKE_PLATFORM_ACCOUNT

pytestmark = pytest.mark.django_db


class CreateAccountMixin:
    @pytest.fixture(autouse=True)
    def create_account(self, monkeypatch):
        """
        Fixture to automatically create and assign the default testing keys to the Platform Account
        """

        def mock_account_retrieve(*args, **kwargs):
            return FAKE_PLATFORM_ACCOUNT

        monkeypatch.setattr(stripe.Account, "retrieve", mock_account_retrieve)

        # create a Stripe Platform Account
        FAKE_PLATFORM_ACCOUNT.create()


@pytest.fixture
def fake_user():
    user = get_user_model().objects.create_user(
        username="testuser", email="testuser@example.com"
    )
    return user


@pytest.fixture
def fake_customer(fake_user):
    customer = FAKE_CUSTOMER.create_for_user(fake_user)
    return customer
