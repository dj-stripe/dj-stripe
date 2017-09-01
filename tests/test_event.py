"""
.. module:: dj-stripe.tests.test_event
   :synopsis: dj-stripe Event Model Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import TestCase
from mock import Mock, patch

from djstripe import webhooks
from djstripe.models import Event, StripeError

from . import FAKE_CUSTOMER, FAKE_EVENT_TRANSFER_CREATED


class EventTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

        patcher = patch.object(webhooks, 'call_handlers')
        self.addCleanup(patcher.stop)
        self.call_handlers = patcher.start()

    def test_str(self):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)

        self.assertEqual("<type={type}, stripe_id={stripe_id}>".format(
            type=FAKE_EVENT_TRANSFER_CREATED["type"],
            stripe_id=FAKE_EVENT_TRANSFER_CREATED["id"]
        ), str(event))

    @patch('djstripe.models.EventProcessingException.log')
    def test_process_event_with_log_stripe_error(self, event_exception_log_mock):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)
        self.call_handlers.side_effect = StripeError("Boom!")
        self.assertFalse(event.process())
        self.assertTrue(event_exception_log_mock.called)
        self.assertFalse(event.processed)

    @patch('djstripe.models.EventProcessingException.log')
    def test_process_event_with_raise_stripe_error(self, event_exception_log_mock):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)
        self.call_handlers.side_effect = StripeError("Boom!")
        with self.assertRaises(StripeError):
            event.process(raise_exception=True)
        self.assertTrue(event_exception_log_mock.called)
        self.assertFalse(event.processed)

    def test_process_event_when_invalid(self):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)
        event.valid = False
        self.assertFalse(event.process())
        self.assertFalse(event.process(force=True))  # no effect

    def test_reprocess_event_not_forced(self):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)
        event.save = Mock()

        self.assertTrue(event.process())
        event.save.assert_called_with()
        event.save.reset_mock()

        self.assertTrue(event.process())
        event.save.assert_not_called()

    def test_reprocess_event_forced(self):
        event = self._create_event(FAKE_EVENT_TRANSFER_CREATED)
        event.save = Mock()

        self.assertTrue(event.process())
        event.save.assert_called_with()
        event.save.reset_mock()

        self.assertTrue(event.process(force=True))
        event.save.assert_called_with()

    #
    # Helpers
    #

    @patch('stripe.Event.retrieve')
    def _create_event(self, event_data, event_retrieve_mock):
        event_data = deepcopy(event_data)
        event_retrieve_mock.return_value = event_data
        event = Event.sync_from_stripe_data(event_data)
        event.validate()
        return event
