"""
Module for creating re-usable fixtures to be used across the test suite
"""
import pytest
from django.contrib.auth import get_user_model

from djstripe.enums import APIKeyType
from djstripe.models import APIKey

from . import FAKE_CUSTOMER, FAKE_PLATFORM_ACCOUNT

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def create_account_and_stripe_apikeys(settings):
    """
    Fixture to automatically create and assign the default testing keys to the Platform Account
    """
    # create a Stripe Platform Account
    djstripe_platform_account = FAKE_PLATFORM_ACCOUNT.create()

    # create and assign APIKey instances to the djstripe Platform Account
    APIKey.objects.get_or_create(
        type=APIKeyType.secret,
        name="Test Secret Key",
        secret=settings.STRIPE_TEST_SECRET_KEY,
        livemode=False,
        djstripe_owner_account=djstripe_platform_account,
    )


@pytest.fixture
def fake_user():
    user = get_user_model().objects.create_user(
        username="arnav", email="arnav13@gmail.com"
    )
    return user


@pytest.fixture
def fake_customer(fake_user):
    customer = FAKE_CUSTOMER.create_for_user(fake_user)
    return customer
