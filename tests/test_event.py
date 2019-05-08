"""
dj-stripe Event Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from stripe.error import StripeError

from djstripe import webhooks
from djstripe.models import Event

from . import FAKE_CUSTOMER, FAKE_EVENT_TRANSFER_CREATED


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
				type=FAKE_EVENT_TRANSFER_CREATED["type"], id=FAKE_EVENT_TRANSFER_CREATED["id"]
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
		mock__create_from_stripe_object.return_value.invoke_webhook_handlers.assert_called_once_with()
		# Make sure the event was returned.
		self.assertEqual(mock__create_from_stripe_object.return_value, result)

	@patch(target="djstripe.models.core.transaction.atomic", autospec=True)
	@patch.object(target=Event, attribute="_create_from_stripe_object", autospec=True)
	@patch.object(target=Event, attribute="objects", autospec=True)
	def test_process_event_exists(
		self, mock_objects, mock__create_from_stripe_object, mock_atomic
	):
		"""Test that process event returns the existing event and skips webhook processing
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
		# Using assert_not_called() doesn't work on this in Python 3.5
		self.assertEqual(mock__create_from_stripe_object.call_count, 0)
		mock__create_from_stripe_object.return_value.invoke_webhook_handlers.assert_not_called()
		# Make sure the existing event was returned.
		self.assertEqual(mock_objects.filter.return_value.first.return_value, result)

	#
	# Helpers
	#

	@patch("stripe.Event.retrieve", autospec=True)
	def _create_event(self, event_data, event_retrieve_mock):
		event_data = deepcopy(event_data)
		event_retrieve_mock.return_value = event_data
		event = Event.sync_from_stripe_data(event_data)
		return event
