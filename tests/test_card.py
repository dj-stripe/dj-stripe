"""
dj-stripe Card Model Tests.
"""

from copy import deepcopy
from unittest.mock import ANY, patch

import pytest
import stripe
from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe import enums
from djstripe.exceptions import StripeObjectManipulationException
from djstripe.models import Account, Card

from . import (
    FAKE_CARD,
    FAKE_CARD_IV,
    FAKE_CUSTOM_ACCOUNT,
    FAKE_CUSTOMER,
    FAKE_STANDARD_ACCOUNT,
    AssertStripeFksMixin,
)
from .conftest import CreateAccountMixin

pytestmark = pytest.mark.django_db


class TestStrCard:
    @pytest.mark.parametrize(
        "fake_stripe_data",
        [
            deepcopy(FAKE_CARD_IV),
        ],
    )
    def test__str__(self, fake_stripe_data, monkeypatch):
        def mock_account_get(*args, **kwargs):
            return deepcopy(FAKE_CUSTOM_ACCOUNT)

        # monkeypatch stripe.Account.retrieve to return the desired json response.
        monkeypatch.setattr(stripe.Account, "retrieve", mock_account_get)

        card = Card.sync_from_stripe_data(fake_stripe_data)

        account = Account.objects.filter(id=fake_stripe_data["account"]).first()

        default = fake_stripe_data["default_for_currency"]
        assert (
            f"{enums.CardBrand.humanize(fake_stripe_data['brand'])} {account.default_currency} {'Default' if default else ''} {fake_stripe_data['last4']}"
            == str(card)
        )


class CardTest(CreateAccountMixin, AssertStripeFksMixin, TestCase):
    def setUp(self):
        # create a Standard Stripe Account
        self.standard_account = FAKE_STANDARD_ACCOUNT.create()

        # create a Custom Stripe Account
        self.custom_account = FAKE_CUSTOM_ACCOUNT.create()

        user = get_user_model().objects.create_user(
            username="testuser", email="djstripe@example.com"
        )
        fake_empty_customer = deepcopy(FAKE_CUSTOMER)
        fake_empty_customer["default_source"] = None
        fake_empty_customer["sources"] = []

        self.customer = fake_empty_customer.create_for_user(user)

    def test_attach_objects_hook_without_account(self):
        card = Card.sync_from_stripe_data(FAKE_CARD)
        self.assertEqual(card.account, None)

    def test_create_card_finds_account_with_customer_absent(self):
        # deepcopy the CardDict object
        FAKE_CARD_DICT = deepcopy(FAKE_CARD)
        # Add account and remove customer
        FAKE_CARD_DICT["account"] = self.standard_account.id
        FAKE_CARD_DICT["customer"] = None

        card = Card.sync_from_stripe_data(FAKE_CARD_DICT)

        self.assertEqual(self.standard_account, card.account)
        self.assertEqual(
            card.get_stripe_dashboard_url(),
            f"https://dashboard.stripe.com/{card.account.id}/settings/payouts",
        )

        self.assert_fks(
            card,
            expected_blank_fks={
                "djstripe.BankAccount.account",
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.default_source",
            },
        )

    @patch("stripe.Token.create", autospec=True)
    def test_card_create_token(self, token_create_mock):
        card = {"number": "4242", "exp_month": 5, "exp_year": 2012, "cvc": 445}
        Card.create_token(**card)

        token_create_mock.assert_called_with(api_key=ANY, card=card)

    def test_api_call_no_account(self):
        exception_message = (
            "Card objects must be manipulated through a Stripe Connected Account. "
            "Pass an Account object into this call."
        )

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            Card._api_create()

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            Card.api_list()

    def test_api_call_bad_account(self):
        exception_message = (
            "Card objects must be manipulated through a Stripe Connected Account. "
            "Pass an Account object into this call."
        )

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            Card._api_create(account="fish")

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            Card.api_list(account="fish")

    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    def test__api_create_with_customer_absent(self, account_retrieve_mock):
        stripe_card = Card._api_create(
            account=self.custom_account, source=FAKE_CARD_IV["id"]
        )

        self.assertEqual(FAKE_CARD_IV, stripe_card)
