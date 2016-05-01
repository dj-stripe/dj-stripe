"""
.. module:: dj-stripe.tests.test_event_handlers
   :synopsis: dj-stripe Event Handler Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
import decimal

from django.test import TestCase
from mock import patch

from djstripe.models import Event, Charge, Transfer
from tests import FAKE_EVENT_CHARGE_SUCCEEDED, FAKE_EVENT_TRANSFER_CREATED


class TestChargeEvents(TestCase):

    @patch("stripe.Event.retrieve")
    def test_charge_created(self, event_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_CHARGE_SUCCEEDED)
        event_retrieve_mock.return_value = fake_stripe_event
        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        charge = Charge.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEquals(charge.amount, fake_stripe_event["data"]["object"]["amount"] / decimal.Decimal("100"))
        self.assertEquals(charge.status, fake_stripe_event["data"]["object"]["status"])


class TestTransferEvents(TestCase):

    @patch("stripe.Event.retrieve")
    def test_transfer_created(self, event_retrieve_mock):
        fake_stripe_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_stripe_event
        event = Event.sync_from_stripe_data(fake_stripe_event)

        event.validate()
        event.process()

        transfer = Transfer.objects.get(stripe_id=fake_stripe_event["data"]["object"]["id"])
        self.assertEquals(transfer.amount, fake_stripe_event["data"]["object"]["amount"] / decimal.Decimal("100"))
        self.assertEquals(transfer.status, fake_stripe_event["data"]["object"]["status"])
