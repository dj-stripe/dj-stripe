"""
dj-stripe Event Model Tests.
"""

from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from stripe import StripeError

from djstripe.models import Event, Transfer
from djstripe.settings import djstripe_settings
from djstripe.signals import WEBHOOK_SIGNALS

from . import (
    FAKE_CUSTOMER,
    FAKE_EVENT_TRANSFER_CREATED,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_TRANSFER,
)
from .conftest import CreateAccountMixin


class EventTest(CreateAccountMixin, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

    def test___str__(self):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)

        self.assertEqual(
            (
                f"type={FAKE_EVENT_TRANSFER_CREATED['type']},"
                f" id={FAKE_EVENT_TRANSFER_CREATED['id']}"
            ),
            str(event),
        )

    def test_invoke_webhook_handlers_event_with_log_stripe_error(self):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)
        signal = WEBHOOK_SIGNALS.get(FAKE_EVENT_TRANSFER_CREATED["type"])
        with patch.object(signal, "send", side_effect=StripeError("Boom!")):
            with self.assertRaises(StripeError):
                event.invoke_webhook_handlers()

    @patch("djstripe.models.Event.invoke_webhook_handlers", autospec=True)
    def test_process_event_failure_rolls_back(self, invoke_webhook_handlers_mock):
        """Test that process event rolls back event creation on error"""

        class HandlerException(Exception):
            pass

        invoke_webhook_handlers_mock.side_effect = HandlerException
        real_create_from_stripe_object = Event._create_from_stripe_object

        def side_effect(*args, **kwargs):
            return real_create_from_stripe_object(*args, **kwargs)

        event_data = deepcopy(FAKE_EVENT_TRANSFER_CREATED)

        self.assertFalse(
            Event.objects.filter(id=FAKE_EVENT_TRANSFER_CREATED["id"]).exists()
        )

        with (
            self.assertRaises(HandlerException),
            patch(
                "djstripe.models.Event._create_from_stripe_object",
                side_effect=side_effect,
                autospec=True,
            ) as create_from_stripe_object_mock,
        ):
            Event.process(data=event_data)

        create_from_stripe_object_mock.assert_called_once_with(
            event_data, api_key=djstripe_settings.STRIPE_SECRET_KEY
        )
        self.assertFalse(
            Event.objects.filter(id=FAKE_EVENT_TRANSFER_CREATED["id"]).exists()
        )

    #
    # Helpers
    #

    @patch("stripe.Event.retrieve", autospec=True)
    def _create_event(self, event_data, event_retrieve_mock):
        event_data = deepcopy(event_data)
        event_retrieve_mock.return_value = event_data
        event = Event.sync_from_stripe_data(event_data)
        return event


class EventRaceConditionTest(TestCase):
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    def test_process_event_race_condition(
        self,
        transfer_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        transfer = Transfer.sync_from_stripe_data(deepcopy(FAKE_TRANSFER))
        transfer_retrieve_mock.reset_mock()
        event_data = deepcopy(FAKE_EVENT_TRANSFER_CREATED)

        # emulate the race condition in _get_or_create_from_stripe_object where
        # an object is created by a different request during the call
        #
        # Sequence of events:
        # 1) first Transfer.stripe_objects.get fails with DoesNotExist
        #    (due to it not existing in reality, but due to our side_effect in the test)
        # 2) object is really created by a different request in reality
        # 3) Transfer._create_from_stripe_object fails with IntegrityError due to
        #    duplicate id
        # 4) second Transfer.stripe_objects.get succeeds
        #    (due to being created by step 2 in reality, due to side effect in the test)
        side_effect = [Transfer.DoesNotExist(), transfer]

        with patch(
            "djstripe.models.Transfer.stripe_objects.get",
            side_effect=side_effect,
            autospec=True,
        ) as transfer_objects_get_mock:
            Event.process(event_data)

        self.assertEqual(transfer_objects_get_mock.call_count, 2)
        self.assertEqual(transfer_retrieve_mock.call_count, 1)

    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    def test_process_duplicate_event_returns_existing(
        self,
        transfer_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        """
        Stripe may deliver the same event more than once (eg. on delivery
        timeouts/retries). If two deliveries race past the existence check, the
        insert raises an IntegrityError on the unique id constraint. process()
        must recover and return the already-stored Event instead of crashing.

        Regression test for
        https://github.com/dj-stripe/dj-stripe/issues/1239
        """
        Transfer.sync_from_stripe_data(deepcopy(FAKE_TRANSFER))
        event_data = deepcopy(FAKE_EVENT_TRANSFER_CREATED)

        # First delivery: the Event is created and processed normally.
        event = Event.process(deepcopy(event_data))
        self.assertEqual(Event.objects.filter(id=event_data["id"]).count(), 1)

        # Second (duplicate) delivery: emulate a concurrent insert by forcing
        # the initial existence check to miss while the row already exists, so
        # the insert fails with an IntegrityError.
        with (
            patch(
                "django.db.models.query.QuerySet.exists",
                return_value=False,
            ),
            patch(
                "djstripe.models.Event._create_from_stripe_object",
                side_effect=IntegrityError(
                    "duplicate key value violates unique constraint"
                    ' "djstripe_event_stripe_id_key"'
                ),
                autospec=True,
            ),
        ):
            result = Event.process(deepcopy(event_data))

        self.assertEqual(result.pk, event.pk)
        self.assertEqual(Event.objects.filter(id=event_data["id"]).count(), 1)

    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
    )
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    def test_process_unrelated_integrity_error_reraises(
        self,
        transfer_retrieve_mock,
        account_retrieve_mock,
        transfer__attach_object_post_save_hook_mock,
    ):
        """
        An IntegrityError that is *not* caused by the Event already existing
        must propagate, so genuine database errors are not silently swallowed.
        """
        Transfer.sync_from_stripe_data(deepcopy(FAKE_TRANSFER))
        event_data = deepcopy(FAKE_EVENT_TRANSFER_CREATED)

        with patch(
            "djstripe.models.Event._create_from_stripe_object",
            side_effect=IntegrityError("some unrelated constraint"),
            autospec=True,
        ):
            with self.assertRaises(IntegrityError):
                Event.process(deepcopy(event_data))

        self.assertFalse(Event.objects.filter(id=event_data["id"]).exists())
