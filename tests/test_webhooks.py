"""
.. module:: dj-stripe.tests.test_webhooks
   :synopsis: dj-stripe Webhook Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from collections import defaultdict
from copy import deepcopy

from django.test import TestCase
from django.test.client import Client
from django.urls import reverse
from mock import Mock, PropertyMock, call, patch

from djstripe import views, webhooks
from djstripe.models import Event, WebhookEventTrigger
from djstripe.webhooks import TEST_EVENT_ID, call_handlers, handler, handler_all

from . import FAKE_EVENT_TEST_CHARGE_SUCCEEDED, FAKE_EVENT_TRANSFER_CREATED, FAKE_TRANSFER


def mock_webhook_handler(webhook_event_trigger):
    webhook_event_trigger.process()


class TestWebhook(TestCase):

    def _send_event(self, event_data):
        return Client().post(
            reverse("djstripe:webhook"),
            json.dumps(event_data),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="PLACEHOLDER"
        )

    @patch("stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER))
    @patch("stripe.Event.retrieve")
    def test_webhook_with_transfer_event(self, event_retrieve_mock, transfer_retrieve_mock):
        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event

        resp = self._send_event(fake_event)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Event.objects.filter(type="transfer.created").exists())

    def test_webhook_with_test_event(self):
        resp = self._send_event(FAKE_EVENT_TEST_CHARGE_SUCCEEDED)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Event.objects.filter(stripe_id=TEST_EVENT_ID).exists())

    @patch.object(views.djstripe_settings, "WEBHOOK_EVENT_CALLBACK", return_value=mock_webhook_handler)
    @patch("stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER))
    @patch("stripe.Event.retrieve")
    def test_webhook_with_custom_callback(
        self, event_retrieve_mock, transfer_retrieve_mock,
        webhook_event_callback_mock
    ):
        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event

        resp = self._send_event(fake_event)
        self.assertEqual(resp.status_code, 200)
        webhook_event_trigger = WebhookEventTrigger.objects.get()
        webhook_event_callback_mock.called_once_with(webhook_event_trigger)

    @patch("stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER))
    @patch("stripe.Event.retrieve")
    def test_webhook_with_transfer_event_duplicate(self, event_retrieve_mock, transfer_retrieve_mock):
        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event

        resp = self._send_event(fake_event)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Event.objects.filter(type="transfer.created").exists())
        self.assertEqual(1, Event.objects.filter(type="transfer.created").count())

        # Duplication
        resp = self._send_event(fake_event)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(1, Event.objects.filter(type="transfer.created").count())


class TestWebhookHandlers(TestCase):
    def setUp(self):
        # Reset state of registrations per test
        patcher = patch.object(webhooks, 'registrations', new_callable=(lambda: defaultdict(list)))
        self.addCleanup(patcher.stop)
        self.registrations = patcher.start()

        patcher = patch.object(webhooks, 'registrations_global', new_callable=list)
        self.addCleanup(patcher.stop)
        self.registrations_global = patcher.start()

    def test_global_handler_registration(self):
        func_mock = Mock()
        handler_all()(func_mock)
        event = self._call_handlers("wib.ble", {"data": "foo"})  # handled
        self.assertEqual(1, func_mock.call_count)
        func_mock.assert_called_with(event=event)

    def test_event_handler_registration(self):
        global_func_mock = Mock()
        handler_all()(global_func_mock)
        func_mock = Mock()
        handler("foo")(func_mock)
        event = self._call_handlers("foo.bar", {"data": "foo"})  # handled
        self._call_handlers("bar.foo", {"data": "foo"})  # not handled
        self.assertEqual(2, global_func_mock.call_count)  # called each time
        self.assertEqual(1, func_mock.call_count)
        func_mock.assert_called_with(event=event)

    def test_event_subtype_handler_registration(self):
        global_func_mock = Mock()
        handler_all()(global_func_mock)
        func_mock = Mock()
        handler("foo.bar")(func_mock)
        event1 = self._call_handlers("foo.bar", {"data": "foo"})  # handled
        event2 = self._call_handlers("foo.bar.wib", {"data": "foo"})  # handled
        self._call_handlers("foo.baz", {"data": "foo"})  # not handled
        self.assertEqual(3, global_func_mock.call_count)  # called each time
        self.assertEqual(2, func_mock.call_count)
        func_mock.assert_has_calls([
            call(event=event1),
            call(event=event2)
        ])

    def test_global_handler_registration_with_function(self):
        func_mock = Mock()
        handler_all(func_mock)
        event = self._call_handlers("wib.ble", {"data": "foo"})  # handled
        self.assertEqual(1, func_mock.call_count)
        func_mock.assert_called_with(event=event)

    def test_event_handle_registation_with_string(self):
        func_mock = Mock()
        handler("foo")(func_mock)
        event = self._call_handlers("foo.bar", {"data": "foo"})  # handled
        self.assertEqual(1, func_mock.call_count)
        func_mock.assert_called_with(event=event)

    def test_event_handle_registation_with_list_of_strings(self):
        func_mock = Mock()
        handler("foo", "bar")(func_mock)
        event1 = self._call_handlers("foo.bar", {"data": "foo"})  # handled
        event2 = self._call_handlers("bar.foo", {"data": "bar"})  # handled
        self.assertEqual(2, func_mock.call_count)
        func_mock.assert_has_calls([
            call(event=event1),
            call(event=event2)
        ])

    #
    # Helpers
    #

    @staticmethod
    def _call_handlers(event_spec, data):
        event = Mock(spec=Event)
        parts = event_spec.split(".")
        category = parts[0]
        verb = ".".join(parts[1:])
        type(event).parts = PropertyMock(return_value=parts)
        type(event).category = PropertyMock(return_value=category)
        type(event).verb = PropertyMock(return_value=verb)
        call_handlers(event=event)
        return event
