"""
dj-stripe Event Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from stripe.error import StripeError

from djstripe import webhooks
from djstripe.models import Event, Transfer

from . import FAKE_CUSTOMER, FAKE_EVENT_TRANSFER_CREATED, FAKE_TRANSFER


class EventTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

        patcher = patch.object(webhooks, "call_handlers")
        self.addCleanup(patcher.stop)
        self.call_handlers = patcher.start()

    def test_str(self):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)

        self.assertEqual(
            "<type={type}, id={id}>".format(
                type=FAKE_EVENT_TRANSFER_CREATED["type"],
                id=FAKE_EVENT_TRANSFER_CREATED["id"],
            ),
            str(event),
        )

    def test_invoke_webhook_handlers_event_with_log_stripe_error(self):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)
        self.call_handlers.side_effect = StripeError("Boom!")
        with self.assertRaises(StripeError):
            event.invoke_webhook_handlers()

    def test_invoke_webhook_handlers_event_with_raise_stripe_error(self):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)
        self.call_handlers.side_effect = StripeError("Boom!")
        with self.assertRaises(StripeError):
            event.invoke_webhook_handlers()

    def test_invoke_webhook_handlers_event_when_invalid(self):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)
        event.valid = False
        event.invoke_webhook_handlers()

    @patch(target="djstripe.models.core.transaction.atomic", autospec=True)
    @patch.object(target=Event, attribute="_create_from_stripe_object", autospec=True)
    @patch.object(target=Event, attribute="objects", autospec=True)
    def test_process_event(
        self, mock_objects, mock__create_from_stripe_object, mock_atomic
    ):
        """Test that process event creates a new event and invokes webhooks
        when the event doesn't already exist.
        """
        # Set up mocks
        mock_objects.filter.return_value.exists.return_value = False
        mock_data = {"id": "foo_id", "other_stuff": "more_things"}

        result = Event.process(data=mock_data)

        # Check that all the expected work was performed
        mock_objects.filter.assert_called_once_with(id=mock_data["id"])
        mock_objects.filter.return_value.exists.assert_called_once_with()
        mock_atomic.return_value.__enter__.assert_called_once_with()
        mock__create_from_stripe_object.assert_called_once_with(mock_data)
        (
            mock__create_from_stripe_object.return_value.invoke_webhook_handlers
        ).assert_called_once_with()
        # Make sure the event was returned.
        self.assertEqual(mock__create_from_stripe_object.return_value, result)

    @patch(target="djstripe.models.core.transaction.atomic", autospec=True)
    @patch.object(target=Event, attribute="_create_from_stripe_object", autospec=True)
    @patch.object(target=Event, attribute="objects", autospec=True)
    def test_process_event_exists(
        self, mock_objects, mock__create_from_stripe_object, mock_atomic
    ):
        """
        Test that process event returns the existing event and skips webhook processing
        when the event already exists.
        """
        # Set up mocks
        mock_objects.filter.return_value.exists.return_value = True
        mock_data = {"id": "foo_id", "other_stuff": "more_things"}

        result = Event.process(data=mock_data)

        # Make sure that the db was queried and the existing results used.
        mock_objects.filter.assert_called_once_with(id=mock_data["id"])
        mock_objects.filter.return_value.exists.assert_called_once_with()
        mock_objects.filter.return_value.first.assert_called_once_with()
        # Make sure the webhook actions and event object creation were not performed.
        mock_atomic.return_value.__enter__.assert_not_called()
        mock__create_from_stripe_object.assert_not_called()
        (
            mock__create_from_stripe_object.return_value.invoke_webhook_handlers
        ).assert_not_called()
        # Make sure the existing event was returned.
        self.assertEqual(mock_objects.filter.return_value.first.return_value, result)

    @patch("djstripe.models.Event.invoke_webhook_handlers", autospec=True)
    def test_process_event_failure_rolls_back(self, invoke_webhook_handlers_mock):
        """Test that process event rolls back event creation on error
        """

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

        with self.assertRaises(HandlerException), patch(
            "djstripe.models.Event._create_from_stripe_object",
            side_effect=side_effect,
            autospec=True,
        ) as create_from_stripe_object_mock:
            Event.process(data=event_data)

        create_from_stripe_object_mock.assert_called_once_with(event_data)
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
    @patch(
        "stripe.Transfer.retrieve", return_value=deepcopy(FAKE_TRANSFER), autospec=True
    )
    def test_process_event_race_condition(self, transfer_retrieve_mock):
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
