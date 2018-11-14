"""
.. module:: dj-stripe.tests.test_webhooks
   :synopsis: dj-stripe Webhook Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

"""
import json
import warnings
from collections import defaultdict
from copy import deepcopy
from importlib import reload
from unittest.mock import Mock, PropertyMock, call, patch

from django.test import TestCase, override_settings
from django.test.client import Client
from django.urls import reverse

from djstripe import settings as djstripe_settings
from djstripe import webhooks
from djstripe.models import Event, WebhookEventTrigger
from djstripe.webhooks import TEST_EVENT_ID, call_handlers, handler, handler_all

from . import (
    FAKE_EVENT_TEST_CHARGE_SUCCEEDED, FAKE_EVENT_TRANSFER_CREATED, FAKE_TRANSFER
)


def mock_webhook_handler(webhook_event_trigger):
    webhook_event_trigger.process()


class TestWebhook(TestCase):

    def tearDown(self):
        reload(djstripe_settings)

    def _send_event(self, event_data):
        return Client().post(
            reverse("djstripe:webhook"),
            json.dumps(event_data),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="PLACEHOLDER"
        )

    def test_webhook_test_event(self):
        resp = self._send_event(FAKE_EVENT_TEST_CHARGE_SUCCEEDED)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Event.objects.filter(id=TEST_EVENT_ID).exists())

    @override_settings(DJSTRIPE_WEBHOOK_VALIDATION="retrieve_event")
    @patch("stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER))
    @patch("stripe.Event.retrieve", return_value=deepcopy(FAKE_EVENT_TRANSFER_CREATED))
    def test_webhook_retrieve_event_fail(self, event_retrieve_mock, transfer_retrieve_mock):
        reload(djstripe_settings)

        invalid_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        invalid_event["id"] = "evt_invalid"
        invalid_event["data"]["valid"] = "not really"

        resp = self._send_event(invalid_event)

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Event.objects.filter(id="evt_invalid").exists())

    @override_settings(DJSTRIPE_WEBHOOK_VALIDATION="retrieve_event")
    @patch("stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER))
    @patch("stripe.Event.retrieve", return_value=deepcopy(FAKE_EVENT_TRANSFER_CREATED))
    def test_webhook_retrieve_event_pass(self, event_retrieve_mock, transfer_retrieve_mock):
        reload(djstripe_settings)

        resp = self._send_event(FAKE_EVENT_TRANSFER_CREATED)

        self.assertEqual(resp.status_code, 200)
        event_retrieve_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            id=FAKE_EVENT_TRANSFER_CREATED["id"]
        )

    @override_settings(DJSTRIPE_WEBHOOK_VALIDATION="verify_signature", DJSTRIPE_WEBHOOK_SECRET="whsec_XXXXX")
    @patch("stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER))
    @patch("stripe.Event.retrieve", return_value=deepcopy(FAKE_EVENT_TRANSFER_CREATED))
    def test_webhook_invalid_verify_signature_fail(self, event_retrieve_mock, transfer_retrieve_mock):
        reload(djstripe_settings)

        invalid_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        invalid_event["id"] = "evt_invalid"
        invalid_event["data"]["valid"] = "not really"

        resp = self._send_event(invalid_event)

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Event.objects.filter(id="evt_invalid").exists())

    @override_settings(DJSTRIPE_WEBHOOK_VALIDATION="verify_signature", DJSTRIPE_WEBHOOK_SECRET="whsec_XXXXX")
    @patch("stripe.WebhookSignature.verify_header", return_value=True)
    @patch("stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER))
    @patch("stripe.Event.retrieve", return_value=deepcopy(FAKE_EVENT_TRANSFER_CREATED))
    def test_webhook_verify_signature_pass(self, event_retrieve_mock, transfer_retrieve_mock, verify_signature_mock):
        reload(djstripe_settings)

        resp = self._send_event(FAKE_EVENT_TRANSFER_CREATED)

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Event.objects.filter(id="evt_invalid").exists())
        verify_signature_mock.called_once_with(FAKE_EVENT_TRANSFER_CREATED, {})
        event_retrieve_mock.assert_not_called()

    @override_settings(DJSTRIPE_WEBHOOK_VALIDATION=None)
    @patch("stripe.WebhookSignature.verify_header")
    @patch("stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER))
    @patch("stripe.Event.retrieve", return_value=deepcopy(FAKE_EVENT_TRANSFER_CREATED))
    def test_webhook_no_validation_pass(self, event_retrieve_mock, transfer_retrieve_mock, verify_signature_mock):
        reload(djstripe_settings)

        invalid_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        invalid_event["id"] = "evt_invalid"
        invalid_event["data"]["valid"] = "not really"

        resp = self._send_event(invalid_event)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Event.objects.filter(id="evt_invalid").exists())
        event_retrieve_mock.assert_not_called()
        verify_signature_mock.assert_not_called()

    def test_webhook_no_signature(self):
        self.assertEqual(WebhookEventTrigger.objects.count(), 0)
        resp = Client().post(
            reverse("djstripe:webhook"),
            "{}",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(WebhookEventTrigger.objects.count(), 0)

    def test_webhook_no_remote_addr(self):
        self.assertEqual(WebhookEventTrigger.objects.count(), 0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            Client().post(
                reverse("djstripe:webhook"),
                "{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="PLACEHOLDER",
                REMOTE_ADDR=None
            )

        self.assertEqual(WebhookEventTrigger.objects.count(), 1)
        event_trigger = WebhookEventTrigger.objects.first()
        self.assertEqual(event_trigger.remote_ip, "0.0.0.0")

    @patch.object(djstripe_settings, "WEBHOOK_EVENT_CALLBACK", return_value=mock_webhook_handler)
    @patch("stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER))
    @patch("stripe.Event.retrieve")
    def test_webhook_with_custom_callback(
        self, event_retrieve_mock, transfer_retrieve_mock,
        webhook_event_callback_mock
    ):
        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event

        djstripe_settings.WEBHOOK_SECRET = ""
        resp = self._send_event(fake_event)
        self.assertEqual(resp.status_code, 200)
        webhook_event_trigger = WebhookEventTrigger.objects.get()
        webhook_event_callback_mock.called_once_with(webhook_event_trigger)

    @patch("stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER))
    @patch("stripe.Event.retrieve")
    def test_webhook_with_transfer_event_duplicate(self, event_retrieve_mock, transfer_retrieve_mock):
        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event

        djstripe_settings.WEBHOOK_SECRET = ""
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
