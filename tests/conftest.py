"""
Module for creating re-usable fixtures to be used across the test suite
"""
import os

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


def pytest_collection_modifyitems(items, config):
    """Override Pytest config at run-time to run tests using Stripe API only if explictly specified using `-m stripe_api`"""
    # get passed in markers
    markexpr = config.getoption("markexpr")
    if markexpr:
        # allow passed in markers to run
        config.option.markexpr = markexpr
    else:
        # skip running `stripe_api` marked tests unless explictly specified
        for item in items:
            if "stripe_api" in item.keywords:
                # add message to let user know how to run tests using Stripe API
                item.add_marker(
                    pytest.mark.skip(reason="need -m stripe_api option to run")
                )


@pytest.fixture
def configure_settings(settings):
    settings.STRIPE_TEST_SECRET_KEY = settings.STRIPE_SECRET_KEY = os.environ.get(
        "STRIPE_TEST_SECRET_KEY"
    )


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
