"""
dj-stripe Card Model Tests.
"""
from copy import deepcopy
from unittest.mock import ANY, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from stripe.error import InvalidRequestError

from djstripe.exceptions import StripeObjectManipulationException
from djstripe.models import Card

from . import (
	FAKE_CARD, FAKE_CARD_III, FAKE_CARD_V, FAKE_CUSTOMER,
	AssertStripeFksMixin, default_account
)


class CardTest(AssertStripeFksMixin, TestCase):
	def setUp(self):
		self.account = default_account()
		self.user = get_user_model().objects.create_user(
			username="testuser", email="djstripe@example.com"
		)
		self.customer = FAKE_CUSTOMER.create_for_user(self.user)
		self.customer.sources.all().delete()
		self.customer.legacy_cards.all().delete()

	def test_attach_objects_hook_without_customer(self):
		card = Card.sync_from_stripe_data(deepcopy(FAKE_CARD_III))
		self.assertEqual(card.customer, None)

	def test_create_card_finds_customer(self):
		card = Card.sync_from_stripe_data(deepcopy(FAKE_CARD))

		self.assertEqual(self.customer, card.customer)
		self.assertEqual(
			card.get_stripe_dashboard_url(), self.customer.get_stripe_dashboard_url()
		)

	def test_str(self):
		fake_card = deepcopy(FAKE_CARD)
		card = Card.sync_from_stripe_data(fake_card)

		self.assertEqual(
			"<brand={brand}, last4={last4}, exp_month={exp_month}, exp_year={exp_year}, id={id}>".format(
				brand=fake_card["brand"],
				last4=fake_card["last4"],
				exp_month=fake_card["exp_month"],
				exp_year=fake_card["exp_year"],
				id=fake_card["id"],
			),
			str(card),
		)

		self.assert_fks(card, expected_blank_fks={"djstripe.Customer.coupon"})

	@patch("stripe.Token.create")
	def test_card_create_token(self, token_create_mock):
		card = {"number": "4242", "exp_month": 5, "exp_year": 2012, "cvc": 445}
		Card.create_token(**card)

		token_create_mock.assert_called_with(api_key=ANY, card=card)

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
		stripe_card = Card._api_create(customer=self.customer, source=FAKE_CARD["id"])

		self.assertEqual(FAKE_CARD, stripe_card)

	@patch("tests.CardDict.delete")
	@patch("stripe.Card.retrieve", return_value=deepcopy(FAKE_CARD))
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_remove(self, customer_retrieve_mock, card_retrieve_mock, card_delete_mock):
		stripe_card = Card._api_create(customer=self.customer, source=FAKE_CARD["id"])
		Card.sync_from_stripe_data(stripe_card)

		self.assertEqual(1, self.customer.legacy_cards.count())

		card = self.customer.legacy_cards.all()[0]
		card.remove()

		self.assertEqual(0, self.customer.legacy_cards.count())
		self.assertTrue(card_delete_mock.called)

	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_remove_already_deleted_card(self, customer_retrieve_mock):
		stripe_card = Card._api_create(customer=self.customer, source=FAKE_CARD["id"])
		Card.sync_from_stripe_data(stripe_card)

		self.assertEqual(self.customer.legacy_cards.count(), 1)
		card_object = self.customer.legacy_cards.first()
		Card.objects.filter(id=stripe_card["id"]).delete()
		self.assertEqual(self.customer.legacy_cards.count(), 0)
		card_object.remove()
		self.assertEqual(self.customer.legacy_cards.count(), 0)

	@patch("djstripe.models.Card._api_delete")
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_remove_no_such_source(self, customer_retrieve_mock, card_delete_mock):
		stripe_card = Card._api_create(customer=self.customer, source=FAKE_CARD["id"])
		Card.sync_from_stripe_data(stripe_card)

		card_delete_mock.side_effect = InvalidRequestError("No such source:", "blah")

		self.assertEqual(1, self.customer.legacy_cards.count())

		card = self.customer.legacy_cards.all()[0]
		card.remove()

		self.assertEqual(0, self.customer.legacy_cards.count())
		self.assertTrue(card_delete_mock.called)

	@patch("djstripe.models.Card._api_delete")
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_remove_no_such_customer(self, customer_retrieve_mock, card_delete_mock):
		stripe_card = Card._api_create(customer=self.customer, source=FAKE_CARD["id"])
		Card.sync_from_stripe_data(stripe_card)

		card_delete_mock.side_effect = InvalidRequestError("No such customer:", "blah")

		self.assertEqual(1, self.customer.legacy_cards.count())

		card = self.customer.legacy_cards.all()[0]
		card.remove()

		self.assertEqual(0, self.customer.legacy_cards.count())
		self.assertTrue(card_delete_mock.called)

	@patch("djstripe.models.Card._api_delete")
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_remove_unexpected_exception(self, customer_retrieve_mock, card_delete_mock):
		stripe_card = Card._api_create(customer=self.customer, source=FAKE_CARD["id"])
		Card.sync_from_stripe_data(stripe_card)

		card_delete_mock.side_effect = InvalidRequestError("Unexpected Exception", "blah")

		self.assertEqual(1, self.customer.legacy_cards.count())

		card = self.customer.legacy_cards.all()[0]

		with self.assertRaisesMessage(InvalidRequestError, "Unexpected Exception"):
			card.remove()

	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_api_list(self, customer_retrieve_mock):
		card_list = Card.api_list(customer=self.customer)

		self.assertEqual([FAKE_CARD, FAKE_CARD_V], card_list)
