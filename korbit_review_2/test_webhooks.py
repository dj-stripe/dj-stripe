"""
dj-stripe Webhook Tests.
"""

import json
import warnings
from copy import deepcopy
from unittest.mock import patch
from uuid import UUID

import pytest
from django.http.request import HttpHeaders
from django.test import TestCase, override_settings
from django.test.client import Client
from django.urls import reverse

from djstripe.models import Event, Transfer, WebhookEventTrigger
from djstripe.models.webhooks import WebhookEndpoint, get_remote_ip
from djstripe.settings import djstripe_settings

from . import (
    FAKE_CUSTOM_ACCOUNT,
    FAKE_EVENT_TEST_CHARGE_SUCCEEDED,
    FAKE_EVENT_TRANSFER_CREATED,
    FAKE_STANDARD_ACCOUNT,
    FAKE_TRANSFER,
    FAKE_WEBHOOK_ENDPOINT_1,
)
from .conftest import CreateAccountMixin

pytestmark = pytest.mark.django_db


def mock_webhook_handler(webhook_event_trigger):
    webhook_event_trigger.process()


class TestWebhookEventTrigger(CreateAccountMixin, TestCase):
    """Test class to test WebhookEventTrigger model and its methods"""

    def _send_event(self, event_data):
        return Client().post(
            reverse("djstripe:webhook"),
            json.dumps(event_data),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="PLACEHOLDER",
        )

    def _send_event_webhook_endpoint(self, event_data, uuid):
        return Client().post(
            reverse(
                "djstripe:djstripe_webhook_by_uuid",
                kwargs={"uuid": uuid},
            ),
            json.dumps(event_data),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="PLACEHOLDER",
        )

    def test_webhook_test_event(self):
        self.assertEqual(WebhookEventTrigger.objects.count(), 0)
        resp = self._send_event(FAKE_EVENT_TEST_CHARGE_SUCCEEDED)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(WebhookEventTrigger.objects.count(), 1)

    def test___str__(self):
        self.assertEqual(WebhookEventTrigger.objects.count(), 0)
        resp = self._send_event(FAKE_EVENT_TEST_CHARGE_SUCCEEDED)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(WebhookEventTrigger.objects.count(), 1)
        webhookeventtrigger = WebhookEventTrigger.objects.first()

        self.assertEqual(
            (
                f"id={webhookeventtrigger.id}, valid={webhookeventtrigger.valid},"
                f" processed={webhookeventtrigger.processed}"
            ),
            str(webhookeventtrigger),
        )

    @override_settings(DJSTRIPE_WEBHOOK_VALIDATION="retrieve_event")
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_TRANSFER_CREATED),
        autospec=True,
    )
    def test_webhook_retrieve_event_fail(
        self,
        event_retrieve_mock,
        transfer_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        invalid_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        invalid_event["id"] = "evt_invalid"
        invalid_event["data"]["valid"] = "not really"

        resp = self._send_event(invalid_event)

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Event.objects.filter(id="evt_invalid").exists())

    @patch.object(
        WebhookEventTrigger.validate,
        "__defaults__",
        (None, "whsec_XXXXX", 300, "retrieve_event"),
    )
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_TRANSFER_CREATED),
        autospec=True,
    )
    def test_webhook_retrieve_event_pass(
        self,
        event_retrieve_mock,
        transfer_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        resp = self._send_event(FAKE_EVENT_TRANSFER_CREATED)

        self.assertEqual(resp.status_code, 200)
        event_retrieve_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            stripe_version=FAKE_EVENT_TRANSFER_CREATED["api_version"],
            id=FAKE_EVENT_TRANSFER_CREATED["id"],
        )

    @override_settings(
        DJSTRIPE_WEBHOOK_VALIDATION="verify_signature",
    )
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_TRANSFER_CREATED),
        autospec=True,
    )
    def test_webhook_invalid_verify_signature_fail(
        self,
        event_retrieve_mock,
        transfer_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        invalid_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        invalid_event["id"] = "evt_invalid"
        invalid_event["data"]["valid"] = "not really"

        resp = self._send_event(invalid_event)

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Event.objects.filter(id="evt_invalid").exists())

    @override_settings(
        DJSTRIPE_WEBHOOK_VALIDATION="verify_signature",
    )
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.WebhookSignature.verify_header",
        return_value=True,
        autospec=True,
    )
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_TRANSFER_CREATED),
        autospec=True,
    )
    def test_webhook_verify_signature_pass(
        self,
        event_retrieve_mock,
        transfer_retrieve_mock,
        account_retrieve_mock,
        verify_header_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        resp = self._send_event(FAKE_EVENT_TRANSFER_CREATED)

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Event.objects.filter(id="evt_invalid").exists())
        event_retrieve_mock.assert_not_called()

    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.WebhookSignature.verify_header",
        return_value=True,
        autospec=True,
    )
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_TRANSFER_CREATED),
        autospec=True,
    )
    def test_webhook_endpoint_valid_tolerance_pass(
        self,
        event_retrieve_mock,
        transfer_retrieve_mock,
        account_retrieve_mock,
        verify_header_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        # Create WebhookEndpoint
        fake_webhook = deepcopy(FAKE_WEBHOOK_ENDPOINT_1)
        fake_webhook["secret"] = "whsec_XXXXX"
        fake_webhook["tolerance"] = 500
        webhook_endpoint = WebhookEndpoint.sync_from_stripe_data(fake_webhook)

        valid_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        resp = self._send_event_webhook_endpoint(
            valid_event, webhook_endpoint.djstripe_uuid
        )

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Event.objects.filter(id="evt_invalid").exists())
        event_retrieve_mock.assert_not_called()

    @patch.object(
        WebhookEventTrigger.validate, "__defaults__", (None, "whsec_XXXXX", 300, None)
    )
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch("stripe.WebhookSignature.verify_header", autospec=True)
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    @patch(
        "stripe.Event.retrieve",
        return_value=deepcopy(FAKE_EVENT_TRANSFER_CREATED),
        autospec=True,
    )
    def test_webhook_no_validation_pass(
        self,
        event_retrieve_mock,
        transfer_retrieve_mock,
        account_retrieve_mock,
        verify_header_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        invalid_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        invalid_event["id"] = "evt_invalid"
        invalid_event["data"]["valid"] = "not really"

        # ensure warning is raised
        with pytest.warns(None, match=r"WEBHOOK VALIDATION is disabled."):
            resp = self._send_event(invalid_event)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Event.objects.filter(id="evt_invalid").exists())
        event_retrieve_mock.assert_not_called()
        verify_header_mock.assert_not_called()

    def test_webhook_no_signature(self):
        self.assertEqual(WebhookEventTrigger.objects.count(), 0)
        resp = Client().post(
            reverse("djstripe:webhook"), "{}", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(WebhookEventTrigger.objects.count(), 0)

    def test_webhook_remote_addr_is_none(self):
        self.assertEqual(WebhookEventTrigger.objects.count(), 0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            Client().post(
                reverse("djstripe:webhook"),
                "{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="PLACEHOLDER",
                REMOTE_ADDR=None,
            )

        self.assertEqual(WebhookEventTrigger.objects.count(), 1)
        event_trigger = WebhookEventTrigger.objects.first()
        self.assertEqual(event_trigger.remote_ip, "0.0.0.0")

    def test_webhook_remote_addr_is_empty_string(self):
        self.assertEqual(WebhookEventTrigger.objects.count(), 0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            Client().post(
                reverse("djstripe:webhook"),
                "{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="PLACEHOLDER",
                REMOTE_ADDR="",
            )

        self.assertEqual(WebhookEventTrigger.objects.count(), 1)
        event_trigger = WebhookEventTrigger.objects.first()
        self.assertEqual(event_trigger.remote_ip, "0.0.0.0")

    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "djstripe.models.WebhookEventTrigger.validate", return_value=True, autospec=True
    )
    @patch("djstripe.models.WebhookEventTrigger.process", autospec=True)
    def test_webhook_reraise_exception(
        self,
        webhook_event_process_mock,
        webhook_event_validate_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        class ProcessException(Exception):
            pass

        exception_message = "process fail"

        webhook_event_process_mock.side_effect = ProcessException(exception_message)

        self.assertEqual(WebhookEventTrigger.objects.count(), 0)

        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)

        with self.assertRaisesMessage(ProcessException, exception_message):
            self._send_event(fake_event)

        self.assertEqual(WebhookEventTrigger.objects.count(), 1)
        event_trigger = WebhookEventTrigger.objects.first()
        self.assertEqual(event_trigger.exception, exception_message)

    @patch.object(
        WebhookEventTrigger.validate, "__defaults__", (None, "whsec_XXXXX", 300, None)
    )
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch.object(
        djstripe_settings, "WEBHOOK_EVENT_CALLBACK", return_value=mock_webhook_handler
    )
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_webhook_with_custom_callback(
        self,
        event_retrieve_mock,
        transfer_retrieve_mock,
        account_retrieve_mock,
        webhook_event_callback_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event
        with pytest.warns(None):
            resp = self._send_event(fake_event)
        self.assertEqual(resp.status_code, 200)
        webhook_event_trigger = WebhookEventTrigger.objects.get()
        webhook_event_callback_mock.called_once_with(webhook_event_trigger)

    @patch.object(
        WebhookEventTrigger.validate, "__defaults__", (None, "whsec_XXXXX", 300, None)
    )
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_webhook_with_transfer_event_duplicate(
        self,
        event_retrieve_mock,
        transfer_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event
        with pytest.warns(None):
            resp = self._send_event(fake_event)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Event.objects.filter(type="transfer.created").exists())
        self.assertEqual(1, Event.objects.filter(type="transfer.created").count())

        # Duplication
        with pytest.warns(None):
            resp = self._send_event(fake_event)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(1, Event.objects.filter(type="transfer.created").count())

    @patch.object(
        WebhookEventTrigger.validate, "__defaults__", (None, "whsec_XXXXX", 300, None)
    )
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_STANDARD_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_webhook_good_platform_account(
        self,
        event_retrieve_mock,
        transfer_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event
        with pytest.warns(None):
            resp = self._send_event(fake_event)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(WebhookEventTrigger.objects.count(), 1)

        event_trigger = WebhookEventTrigger.objects.first()
        self.assertEqual(
            event_trigger.stripe_trigger_account.id, FAKE_STANDARD_ACCOUNT["id"]
        )

    @patch.object(
        WebhookEventTrigger.validate, "__defaults__", (None, "whsec_XXXXX", 300, None)
    )
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_CUSTOM_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_webhook_good_connect_account(
        self,
        event_retrieve_mock,
        transfer_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        fake_event["account"] = FAKE_CUSTOM_ACCOUNT["id"]
        event_retrieve_mock.return_value = fake_event
        with pytest.warns(None):
            resp = self._send_event(fake_event)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(WebhookEventTrigger.objects.count(), 1)

        event_trigger = WebhookEventTrigger.objects.first()
        self.assertEqual(
            event_trigger.stripe_trigger_account.id, FAKE_CUSTOM_ACCOUNT["id"]
        )

    @patch.object(
        WebhookEventTrigger.validate, "__defaults__", (None, "whsec_XXXXX", 300, None)
    )
    @patch.object(target=Event, attribute="invoke_webhook_handlers", autospec=True)
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    @patch("stripe.Event.retrieve", autospec=True)
    def test_webhook_error(
        self,
        event_retrieve_mock,
        transfer_retrieve_mock,
        mock_invoke_webhook_handlers,
    ):
        """Test the case where webhook processing fails to ensure we rollback
        and do not commit the Event object to the database.
        """
        mock_invoke_webhook_handlers.side_effect = KeyError("Test error")

        fake_event = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event
        with self.assertRaises(KeyError):
            with pytest.warns(None):
                self._send_event(fake_event)

        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(WebhookEventTrigger.objects.count(), 1)

        event_trigger = WebhookEventTrigger.objects.first()
        assert event_trigger
        self.assertEqual(event_trigger.exception, "'Test error'")


class TestWebhookHandlers(TestCase):
    def test_webhook_event_trigger_invalid_body(self):
        trigger = WebhookEventTrigger(remote_ip="127.0.0.1", body="invalid json")
        assert not trigger.json_body


class TestGetRemoteIp:
    class RequestClass:
        def __init__(self, data):
            self.data = data

        @property
        def headers(self):
            return HttpHeaders(self.META)

        @property
        def META(self):
            return self.data

    @pytest.mark.parametrize(
        "data",
        [
            {"HTTP_X_FORWARDED_FOR": "127.0.0.1,345.5.5.3,451.1.1.2"},
            {
                "REMOTE_ADDR": "422.0.0.1",
                "HTTP_X_FORWARDED_FOR": "127.0.0.1,345.5.5.3,451.1.1.2",
            },
            {
                "REMOTE_ADDR": "127.0.0.1",
            },
        ],
    )
    def test_get_remote_ip(self, data):
        request = self.RequestClass(data)
        assert get_remote_ip(request) == "127.0.0.1"

    @pytest.mark.parametrize(
        "data",
        [
            {
                "REMOTE_ADDR": "",
            },
            {
                "pqwwe": "127.0.0.1",
            },
        ],
    )
    def test_get_remote_ip_remote_addr_is_none(self, data):
        request = self.RequestClass(data)

        # ensure warning is raised
        with pytest.warns(
            None, match=r"Could not determine remote IP \(missing REMOTE_ADDR\)\."
        ):
            assert get_remote_ip(request) == "0.0.0.0"


class TestWebhookEndpoint(CreateAccountMixin):
    """Test Class to test WebhookEndpoint and its methods"""

    def test_sync_from_stripe_data_non_existent_webhook_endpoint(self):
        fake_webhook = deepcopy(FAKE_WEBHOOK_ENDPOINT_1)
        webhook_endpoint = WebhookEndpoint.sync_from_stripe_data(fake_webhook)

        assert webhook_endpoint.id == fake_webhook["id"]
        assert isinstance(webhook_endpoint.djstripe_uuid, UUID)

        # assert WebHookEndpoint's secret does not exist for a new sync
        assert not webhook_endpoint.secret

    def test_sync_from_stripe_data_existent_webhook_endpoint(self):
        fake_webhook_1 = deepcopy(FAKE_WEBHOOK_ENDPOINT_1)
        webhook_endpoint = WebhookEndpoint.sync_from_stripe_data(fake_webhook_1)
        assert webhook_endpoint
        assert webhook_endpoint.id == fake_webhook_1["id"]
        djstripe_uuid = webhook_endpoint.djstripe_uuid

        assert isinstance(djstripe_uuid, UUID)

        # assert WebHookEndpoint's secret does not exist for a new sync
        assert not webhook_endpoint.secret

        # add a secret to the webhook_endpoint
        fake_webhook_2 = deepcopy(FAKE_WEBHOOK_ENDPOINT_1)
        fake_webhook_2["secret"] = "whsec_rguCE5LMINfRKjmIkxDJM1lOPXkAOQp3"
        webhook_endpoint.secret = fake_webhook_2["secret"]
        webhook_endpoint.save()

        # re-sync the WebhookEndpoint instance
        WebhookEndpoint.sync_from_stripe_data(fake_webhook_2)

        webhook_endpoint.refresh_from_db()
        assert webhook_endpoint.id == fake_webhook_2["id"]
        # assert secret got updated
        assert webhook_endpoint.secret == fake_webhook_2["secret"]

        # assert UUID didn't get regenerated
        assert webhook_endpoint.djstripe_uuid == djstripe_uuid

    def test___str__(self):
        fake_webhook = deepcopy(FAKE_WEBHOOK_ENDPOINT_1)
        webhook_endpoint = WebhookEndpoint.sync_from_stripe_data(fake_webhook)
        assert webhook_endpoint
        assert str(webhook_endpoint) == webhook_endpoint.url
        assert (
            str(webhook_endpoint)
            == "https://dev.example.com/stripe/webhook/f6f9aa0e-cb6c-4e0f-b5ee-5e2b9e0716d8"
        )
