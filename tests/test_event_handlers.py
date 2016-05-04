"""
.. module:: dj-stripe.tests.test_event_handlers
   :synopsis: dj-stripe Event Handler Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
import decimal

from django.test import TestCase
from mock import patch

from djstripe.models import Event, Charge, Transfer, Account
from tests import FAKE_EVENT_CHARGE_SUCCEEDED, FAKE_EVENT_TRANSFER_CREATED, FAKE_CUSTOMER


class TestChargeEvents(TestCase):

    @patch("djstripe.models.Account.get_default_account")
    @patch('stripe.Customer.retrieve', return_value=deepcopy(FAKE_CUSTOMER))
    @patch('stripe.Charge.retrieve')
    @patch("stripe.Event.retrieve")
    def test_charge_created(self, event_retrieve_mock, charge_retrieve_mock, customer_retrieve_mock, account_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_CHARGE_SUCCEEDED)
        event_retrieve_mock.return_value = fake_stripe_event
        charge_retrieve_mock.return_value = fake_stripe_event["data"]["object"]
        account_mock.return_value = Account.objects.create()

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        charge = Charge.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEquals(charge.amount, fake_stripe_event["data"]["object"]["amount"] / decimal.Decimal("100"))
        self.assertEquals(charge.status, fake_stripe_event["data"]["object"]["status"])


class TestTransferEvents(TestCase):

    @patch('stripe.Transfer.retrieve')
    @patch("stripe.Event.retrieve")
    def test_transfer_created(self, event_retrieve_mock, transfer_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event
        transfer_retrieve_mock.return_value = fake_stripe_event["data"]["object"]

        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        transfer = Transfer.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEquals(transfer.amount, fake_stripe_event["data"]["object"]["amount"] / decimal.Decimal("100"))
        self.assertEquals(transfer.status, fake_stripe_event["data"]["object"]["status"])
