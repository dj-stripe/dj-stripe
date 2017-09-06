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
from djstripe.models import Event, EventProcessingException
from djstripe.webhooks import TEST_EVENT_ID, call_handlers, handler, handler_all

from . import FAKE_EVENT_TEST_CHARGE_SUCCEEDED, FAKE_EVENT_TRANSFER_CREATED, FAKE_TRANSFER


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
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Event.objects.filter(type="transfer.created").exists())

    def test_webhook_with_test_event(self):
        resp = Client().post(
            reverse("djstripe:webhook"),
            json.dumps(FAKE_EVENT_TEST_CHARGE_SUCCEEDED),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Event.objects.filter(stripe_id=TEST_EVENT_ID).exists())

    @patch.object(views.djstripe_settings, 'WEBHOOK_EVENT_CALLBACK', return_value=(lambda event: event.process()))
    @patch("stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER))
    @patch("stripe.Event.retrieve")
    def test_webhook_with_custom_callback(self, event_retrieve_mock, transfer_retrieve_mock,
                                          webhook_event_callback_mock):
        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event

        resp = Client().post(
            reverse("djstripe:webhook"),
            json.dumps(fake_event),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        event = Event.objects.get(type="transfer.created")
        webhook_event_callback_mock.called_once_with(event)

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
        self.assertEqual(resp.status_code, 200)
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
