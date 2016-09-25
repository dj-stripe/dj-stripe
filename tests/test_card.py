"""
.. module:: dj-stripe.tests.test_card
   :synopsis: dj-stripe Card Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from mock.mock import patch
from stripe.error import InvalidRequestError

from djstripe.exceptions import StripeObjectManipulationException
from djstripe.models import Account, Card, Customer
from tests import FAKE_CARD, FAKE_CARD_III, FAKE_CARD_V, FAKE_CUSTOMER


class CardTest(TestCase):

    def setUp(self):
        self.account = Account.objects.create()

    def test_attach_objects_hook_without_customer(self):
        with self.assertRaisesMessage(ValidationError, "A customer was not attached to this card."):
            Card.sync_from_stripe_data(deepcopy(FAKE_CARD_III))

    def test_create_card_finds_customer(self):
        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        customer = Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

        card = Card.sync_from_stripe_data(deepcopy(FAKE_CARD))

        self.assertEqual(customer, card.customer)

    def test_str(self):
        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

        fake_card = deepcopy(FAKE_CARD)
        card = Card.sync_from_stripe_data(fake_card)

        self.assertEqual(
            "<brand={brand}, last4={last4}, exp_month={exp_month}, exp_year={exp_year}, stripe_id={stripe_id}>".format(
                brand=fake_card["brand"],
                last4=fake_card["last4"],
                exp_month=fake_card["exp_month"],
                exp_year=fake_card["exp_year"],
                stripe_id=fake_card["id"]
            ),
            str(card)
        )

    @patch("stripe.Token.create")
    def test_card_create_token(self, token_create_mock):
        card = {"number": "4242", "exp_month": 5, "exp_year": 2012, "cvc": 445}
        Card.create_token(**card)

        token_create_mock.assert_called_with(card=card)

    def test_api_call_no_customer(self):
        exception_message = "Cards must be manipulated through a Customer. Pass a Customer object into this call."

        with self.assertRaisesMessage(StripeObjectManipulationException, exception_message):
            Card._api_create()

        with self.assertRaisesMessage(StripeObjectManipulationException, exception_message):
            Card.api_list()

    def test_api_call_bad_customer(self):
        exception_message = "Cards must be manipulated through a Customer. Pass a Customer object into this call."

        with self.assertRaisesMessage(StripeObjectManipulationException, exception_message):
            Card._api_create(customer="fish")

        with self.assertRaisesMessage(StripeObjectManipulationException, exception_message):
            Card.api_list(customer="fish")

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_api_create(self, customer_retrieve_mock):
        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        customer = Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        stripe_card = Card._api_create(customer=customer, source=FAKE_CARD["id"])

        self.assertEqual(FAKE_CARD, stripe_card)

    @patch("tests.CardDict.delete")
    @patch("stripe.Card.retrieve", return_value=deepcopy(FAKE_CARD))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_remove(self, customer_retrieve_mock, card_retrieve_mock, card_delete_mock):
        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        customer = Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        stripe_card = Card._api_create(customer=customer, source=FAKE_CARD["id"])
        Card.sync_from_stripe_data(stripe_card)

        self.assertEqual(1, customer.sources.count())

        card = customer.sources.all()[0]
        card.remove()

        self.assertEqual(0, customer.sources.count())
        self.assertTrue(card_delete_mock.called)

    @patch("djstripe.models.Card._api_delete")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_remove_exception(self, customer_retrieve_mock, card_delete_mock):
        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        customer = Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        stripe_card = Card._api_create(customer=customer, source=FAKE_CARD["id"])
        Card.sync_from_stripe_data(stripe_card)

        card_delete_mock.side_effect = InvalidRequestError("No such customer:", "blah")

        self.assertEqual(1, customer.sources.count())

        card = customer.sources.all()[0]
        card.remove()

        self.assertEqual(0, customer.sources.count())
        self.assertTrue(card_delete_mock.called)

    @patch("djstripe.models.Card._api_delete")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_remove_unexpected_exception(self, customer_retrieve_mock, card_delete_mock):
        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        customer = Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        stripe_card = Card._api_create(customer=customer, source=FAKE_CARD["id"])
        Card.sync_from_stripe_data(stripe_card)

        card_delete_mock.side_effect = InvalidRequestError("Unexpected Exception", "blah")

        self.assertEqual(1, customer.sources.count())

        card = customer.sources.all()[0]

        with self.assertRaisesMessage(InvalidRequestError, "Unexpected Exception"):
            card.remove()

    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_api_list(self, customer_retrieve_mock):
        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        customer = Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        card_list = Card.api_list(customer=customer)

        self.assertEqual([FAKE_CARD, FAKE_CARD_V], card_list)
