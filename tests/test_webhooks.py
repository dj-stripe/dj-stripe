"""
.. module:: dj-stripe.tests.test_webhooks
   :synopsis: dj-stripe Webhook Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from mock import patch

from djstripe.models import Event, EventProcessingException
from tests import FAKE_EVENT_TRANSFER_CREATED, FAKE_TRANSFER


class TestWebhook(TestCase):

    @patch("stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER))
    @patch("stripe.Event.retrieve")
    def test_webhook_with_transfer_event(self, event_retrieve_mock, transfer_retrieve_mock):
        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event

        resp = Client().post(
            reverse("djstripe:webhook"),
            json.dumps(fake_event),
            content_type="application/json"
        )
        self.assertEquals(resp.status_code, 200)
        self.assertTrue(Event.objects.filter(type="transfer.created").exists())

    @patch("stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER))
    @patch("stripe.Event.retrieve")
    def test_webhook_with_transfer_event_duplicate(self, event_retrieve_mock, transfer_retrieve_mock):
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
