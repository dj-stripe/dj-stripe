"""
dj-stripe Card Model Tests.
"""

import uuid
from copy import deepcopy
from unittest.mock import ANY, patch

import pytest
import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe import enums
from djstripe.exceptions import StripeObjectManipulationException
from djstripe.models import Account, Card, Customer

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
        "fake_stripe_data, has_account, has_customer",
        [
            (deepcopy(FAKE_CARD), False, True),
            (deepcopy(FAKE_CARD_IV), True, False),
        ],
    )
    def test__str__(self, fake_stripe_data, has_account, has_customer, monkeypatch):
        def mock_customer_get(*args, **kwargs):
            data = deepcopy(FAKE_CUSTOMER)
            data["default_source"] = None
            data["sources"] = []
            return data

        def mock_account_get(*args, **kwargs):
            return deepcopy(FAKE_CUSTOM_ACCOUNT)

        # monkeypatch stripe.Account.retrieve and stripe.Customer.retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Account, "retrieve", mock_account_get)
        monkeypatch.setattr(stripe.Customer, "retrieve", mock_customer_get)

        card = Card.sync_from_stripe_data(fake_stripe_data)
        default = False

        if has_account:
            account = Account.objects.filter(id=fake_stripe_data["account"]).first()

            default = fake_stripe_data["default_for_currency"]
            assert (
                f"{enums.CardBrand.humanize(fake_stripe_data['brand'])} {account.default_currency} {'Default' if default else ''} {fake_stripe_data['last4']}"
                == str(card)
            )
        if has_customer:
            customer = Customer.objects.filter(id=fake_stripe_data["customer"]).first()

            default_source = customer.default_source
            default_payment_method = customer.default_payment_method

            if (
                default_payment_method
                and fake_stripe_data["id"] == default_payment_method.id
            ) or (default_source and fake_stripe_data["id"] == default_source.id):
                # current card is the default payment method or source
                default = True

            assert (
                f"{enums.CardBrand.humanize(fake_stripe_data['brand'])} {fake_stripe_data['last4']} {'Default' if default else ''} Expires"
                f" {fake_stripe_data['exp_month']} {fake_stripe_data['exp_year']}"
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

    def test_attach_objects_hook_without_customer(self):
        FAKE_CARD_DICT = deepcopy(FAKE_CARD)
        FAKE_CARD_DICT["customer"] = None

        card = Card.sync_from_stripe_data(FAKE_CARD_DICT)
        self.assertEqual(card.customer, None)

    def test_attach_objects_hook_without_account(self):
        card = Card.sync_from_stripe_data(FAKE_CARD)
        self.assertEqual(card.account, None)

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Account.retrieve_external_account",
        return_value=deepcopy(FAKE_CARD),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve_source",
        return_value=deepcopy(FAKE_CARD),
        autospec=True,
    )
    def test_api_retrieve_by_customer_equals_retrieval_by_account(
        self,
        customer_retrieve_source_mock,
        account_retrieve_external_account_mock,
        customer_retrieve_mock,
    ):
        # deepcopy the CardDict object
        FAKE_CARD_DICT = deepcopy(FAKE_CARD)

        card_by_customer = Card.sync_from_stripe_data(
            deepcopy(FAKE_CARD_DICT)
        ).api_retrieve()

        # Add account
        FAKE_CARD_DICT["account"] = FAKE_CUSTOM_ACCOUNT["id"]
        FAKE_CARD_DICT["customer"] = None

        card_by_account = Card.sync_from_stripe_data(FAKE_CARD_DICT).api_retrieve()

        # assert the same card object gets retrieved
        self.assertCountEqual(card_by_customer, card_by_account)

    def test_create_card_finds_customer_with_account_absent(self):
        card = Card.sync_from_stripe_data(FAKE_CARD)

        self.assertEqual(self.customer, card.customer)
        self.assertEqual(
            card.get_stripe_dashboard_url(), self.customer.get_stripe_dashboard_url()
        )

        self.assert_fks(
            card,
            expected_blank_fks={
                "djstripe.Card.account",
                "djstripe.BankAccount.account",
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.default_source",
            },
        )

    def test_create_card_finds_customer_with_account_present(self):
        # deepcopy the CardDict object
        FAKE_CARD_DICT = deepcopy(FAKE_CARD)
        # Add account
        FAKE_CARD_DICT["account"] = self.standard_account.id

        card = Card.sync_from_stripe_data(FAKE_CARD_DICT)

        self.assertEqual(self.customer, card.customer)
        self.assertEqual(self.standard_account, card.account)
        self.assertEqual(
            card.get_stripe_dashboard_url(),
            self.customer.get_stripe_dashboard_url(),
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
                "djstripe.Card.customer",
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

    def test_api_call_no_customer_and_no_account(self):
        exception_message = (
            "Card objects must be manipulated through either a Stripe Connected Account"
            " or a customer. Pass a Customer or an Account object into this call."
        )

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            Card._api_create()

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            Card.api_list()

    def test_api_call_bad_customer(self):
        exception_message = (
            "Card objects must be manipulated through a Customer. "
            "Pass a Customer object into this call."
        )

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            Card._api_create(customer="fish")

        with self.assertRaisesMessage(
            StripeObjectManipulationException, exception_message
        ):
            Card.api_list(customer="fish")

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
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test__api_create_with_account_absent(self, customer_retrieve_mock):
        stripe_card = Card._api_create(customer=self.customer, source=FAKE_CARD["id"])

        self.assertEqual(FAKE_CARD, stripe_card)

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

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    def test__api_create_with_customer_and_account(
        self, account_retrieve_mock, customer_retrieve_mock
    ):
        FAKE_CARD_DICT = deepcopy(FAKE_CARD)
        FAKE_CARD_DICT["account"] = FAKE_CUSTOM_ACCOUNT["id"]

        stripe_card = Card._api_create(
            account=self.custom_account,
            customer=self.customer,
            source=FAKE_CARD_DICT["id"],
        )

        self.assertEqual(FAKE_CARD, stripe_card)

    @patch(
        "stripe.Account.delete_external_account",
        autospec=True,
    )
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    def test_remove_card_by_account(self, account_retrieve_mock, card_delete_mock):
        stripe_card = Card._api_create(
            account=self.custom_account, source=FAKE_CARD_IV["id"]
        )
        card = Card.sync_from_stripe_data(stripe_card)
        self.assertEqual(1, Card.objects.filter(id=stripe_card["id"]).count())

        # remove card
        card.remove()

        self.assertEqual(0, Card.objects.filter(id=stripe_card["id"]).count())

        api_key = card.default_api_key
        stripe_account = card._get_stripe_account_id(api_key)

        card_delete_mock.assert_called_once_with(
            self.custom_account.id,
            card.id,
            api_key=api_key,
            stripe_account=stripe_account,
        )

    @patch(
        "stripe.Account.delete_external_account",
        autospec=True,
    )
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    def test_remove_already_deleted_card_by_account(
        self, account_retrieve_mock, card_delete_mock
    ):
        stripe_card = Card._api_create(
            account=self.custom_account, source=FAKE_CARD_IV["id"]
        )
        card = Card.sync_from_stripe_data(stripe_card)
        self.assertEqual(1, Card.objects.filter(id=stripe_card["id"]).count())

        # remove card
        card.remove()
        self.assertEqual(0, Card.objects.filter(id=stripe_card["id"]).count())

        # remove card again
        count, _ = Card.objects.filter(id=stripe_card["id"]).delete()
        self.assertEqual(0, count)

        api_key = card.default_api_key
        stripe_account = card._get_stripe_account_id(api_key)

        card_delete_mock.assert_called_once_with(
            self.custom_account.id,
            card.id,
            api_key=api_key,
            stripe_account=stripe_account,
        )

    @pytest.mark.stripe_api
    @pytest.mark.usefixtures("configure_settings")
    def test_api_list(self):
        stripe_customer = stripe.Customer.create(
            api_key=settings.STRIPE_SECRET_KEY,
            email=f"card-api-list-{uuid.uuid4().hex}@example.com",
            metadata={"djstripe_test": "card_api_list"},
        )
        try:
            customer = Customer.sync_from_stripe_data(
                stripe_customer, api_key=settings.STRIPE_SECRET_KEY
            )
            stripe_card = Card._api_create(
                customer=customer,
                source="tok_visa",
                api_key=settings.STRIPE_SECRET_KEY,
            )
            stripe_card_id = (
                stripe_card["id"] if isinstance(stripe_card, dict) else stripe_card.id
            )

            card_list = list(
                Card.api_list(
                    customer=customer, api_key=settings.STRIPE_SECRET_KEY, limit=100
                )
            )

            self.assertTrue(any(card.id == stripe_card_id for card in card_list))
        finally:
            stripe.Customer.delete(
                stripe_customer.id, api_key=settings.STRIPE_SECRET_KEY
            )
