"""
.. module:: dj-stripe.tests.test_webhooks
   :synopsis: dj-stripe Webhook Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
import decimal
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from mock import patch

from djstripe.models import Event, EventProcessingException, Transfer
from tests import FAKE_EVENT_TRANSFER_CREATED


class TestWebhook(TestCase):

    @patch("stripe.Event.retrieve")
    def test_webhook_with_transfer_event(self, event_retrieve_mock):
        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event

        resp = Client().post(
            reverse("djstripe:webhook"),
            json.dumps(fake_event),
            content_type="application/json"
        )
        self.assertEquals(resp.status_code, 200)
        self.assertTrue(Event.objects.filter(type="transfer.created").exists())

    @patch("stripe.Event.retrieve")
    def test_webhook_with_transfer_event_duplicate(self, event_retrieve_mock):
        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event

        resp = Client().post(
            reverse("djstripe:webhook"),
            json.dumps(fake_event),
            content_type="application/json"
        )
        self.assertEquals(resp.status_code, 200)
        self.assertTrue(Event.objects.filter(type="transfer.created").exists())
        self.assertEqual(1, Event.objects.filter(type="transfer.created").count())

        # Duplication
        resp = Client().post(
            reverse("djstripe:webhook"),
            json.dumps(fake_event),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(1, Event.objects.filter(type="transfer.created").count())
        self.assertEqual(1, EventProcessingException.objects.count())


class TestTransferWebhooks(TestCase):

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
