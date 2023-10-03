"""
Module for creating re-usable fixtures to be used across the test suite
"""
import os

import pytest
import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from stripe.error import InvalidRequestError, PermissionError

from djstripe import models

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


def pytest_configure(config):
    markexpr = config.getoption("markexpr")
    if markexpr == "stripe_api":
        key = os.environ.get("STRIPE_TEST_SECRET_KEY")
        if not key:
            pytest.exit(
                f"Expected Real Stripe Account Testing key to be provided. Got {key}."
                " Please pass it like so 'STRIPE_TEST_SECRET_KEY=<STRIPE_KEY> pytest"
                " -m stripe_api'"
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


# Stripe Account Fixtures
@pytest.fixture
def standard_account_fixture(django_db_setup, django_db_blocker, configure_settings):
    """Create Standard Stripe Account."""
    # See: https://pytest-django.readthedocs.io/en/latest/database.html#populate-the-test-database-if-you-don-t-use-transactional-or-live-server
    with django_db_blocker.unblock():
        # setup_stuff
        account_json = models.Account._api_create(
            type="standard",
            country="US",
            email="jenny.standard.rosen@example.com",
            api_key=settings.STRIPE_SECRET_KEY,
        )
        account_instance = models.Account.sync_from_stripe_data(
            account_json,
            api_key=settings.STRIPE_SECRET_KEY,
        )

        yield account_json, account_instance

        # teardown_stuff
        try:
            # try to delete
            account_instance._api_delete(api_key=settings.STRIPE_SECRET_KEY)
        except (InvalidRequestError, PermissionError):
            pass


@pytest.fixture
def custom_account_fixture(django_db_setup, django_db_blocker, configure_settings):
    """Create Custom Stripe Account."""
    # See: https://pytest-django.readthedocs.io/en/latest/database.html#populate-the-test-database-if-you-don-t-use-transactional-or-live-server
    with django_db_blocker.unblock():
        # setup_stuff
        account_json = models.Account._api_create(
            type="custom",
            country="US",
            email="jenny.custom.rosen@example.com",
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
            api_key=settings.STRIPE_SECRET_KEY,
        )
        account_instance = models.Account.sync_from_stripe_data(
            account_json,
            api_key=settings.STRIPE_SECRET_KEY,
        )

        yield account_json, account_instance

        # teardown_stuff
        try:
            # try to delete
            account_instance._api_delete(api_key=settings.STRIPE_SECRET_KEY)
        except (InvalidRequestError, PermissionError):
            pass


@pytest.fixture
def custom_account_func_fixture(django_db_setup, django_db_blocker, configure_settings):
    """
    Same as custom_account_fixture but functional.

    This is useful for tests involving rejecting and deleting instances.
    """
    # See: https://pytest-django.readthedocs.io/en/latest/database.html#populate-the-test-database-if-you-don-t-use-transactional-or-live-server
    with django_db_blocker.unblock():
        # setup_stuff
        account_json = models.Account._api_create(
            type="custom",
            country="US",
            email="jenny.custom.rosen@example.com",
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
            api_key=settings.STRIPE_SECRET_KEY,
        )
        account_instance = models.Account.sync_from_stripe_data(
            account_json,
            api_key=settings.STRIPE_SECRET_KEY,
        )

        yield account_json, account_instance

        # teardown_stuff
        try:
            # try to delete
            account_instance._api_delete(api_key=settings.STRIPE_SECRET_KEY)
        except (InvalidRequestError, PermissionError):
            pass


@pytest.fixture
def platform_account_fixture(django_db_setup, django_db_blocker, configure_settings):
    """Retrieve Platform Stripe Account."""
    # See: https://pytest-django.readthedocs.io/en/latest/database.html#populate-the-test-database-if-you-don-t-use-transactional-or-live-server
    with django_db_blocker.unblock():
        # setup_stuff
        account_json = stripe.Account.retrieve(
            api_key=settings.STRIPE_SECRET_KEY,
        )
        account_instance = models.Account.sync_from_stripe_data(
            account_json,
            api_key=settings.STRIPE_SECRET_KEY,
        )

        yield account_json, account_instance
