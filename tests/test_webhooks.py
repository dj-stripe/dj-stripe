"""
.. module:: dj-stripe.tests.test_webhooks
   :synopsis: dj-stripe Webhook Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
from collections import defaultdict
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from mock import patch, Mock, ANY

from djstripe import webhooks
from djstripe.models import Event, EventProcessingException
from djstripe.webhooks import handler, handler_all, call_handlers
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


class TestWebhookHandlers(TestCase):
    def setUp(self):
        # Reset state of registrations per test
        patcher = patch.object(
            webhooks, 'registrations', new_callable=lambda: defaultdict(list))
        self.addCleanup(patcher.stop)
        self.registrations = patcher.start()

        patcher = patch.object(
            webhooks, 'registrations_global', new_callable=list)
        self.addCleanup(patcher.stop)
        self.registrations_global = patcher.start()

    def test_global_handler_registration(self):
        func_mock = Mock()
        handler_all()(func_mock)
        call_handlers(Mock(), {'data': 'foo'}, 'wib', 'ble')  # handled
        self.assertEqual(1, func_mock.call_count)

    def test_event_handler_registration(self):
        global_func_mock = Mock()
        handler_all()(global_func_mock)
        func_mock = Mock()
        handler(['foo'])(func_mock)
        call_handlers(Mock(), {'data': 'foo'}, 'foo', 'bar')  # handled
        call_handlers(Mock(), {'data': 'foo'}, 'bar', 'foo')  # not handled
        self.assertEqual(2, global_func_mock.call_count)  # called each time
        self.assertEqual(1, func_mock.call_count)
        func_mock.assert_called_with(ANY, ANY, 'foo', 'bar')

    def test_event_subtype_handler_registration(self):
        global_func_mock = Mock()
        handler_all()(global_func_mock)
        func_mock = Mock()
        handler(['foo.bar'])(func_mock)
        call_handlers(Mock(), {'data': 'foo'}, 'foo', 'bar')  # handled
        call_handlers(Mock(), {'data': 'foo'}, 'foo', 'baz')  # not handled
        self.assertEqual(2, global_func_mock.call_count)  # called each time
        self.assertEqual(1, func_mock.call_count)
        func_mock.assert_called_with(ANY, ANY, 'foo', 'bar')

    def test_global_handler_registration_with_function(self):
        func_mock = Mock()
        handler_all(func_mock)
        call_handlers(Mock(), {'data': 'foo'}, 'wib', 'ble')  # handled
        self.assertEqual(1, func_mock.call_count)

    def test_event_handle_registation_with_string(self):
        func_mock = Mock()
        handler('foo')(func_mock)
        call_handlers(Mock(), {'data': 'foo'}, 'foo', 'bar')  # handled
        self.assertEqual(1, func_mock.call_count)
