"""
.. module:: dj-stripe.tests.test_event
   :synopsis: dj-stripe Event Model Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import TestCase
from mock import patch

from djstripe.models import Customer, Event
from tests import FAKE_EVENT_TRANSFER_CREATED, FAKE_CUSTOMER


class EventTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        self.customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

    def test_str(self):
        event = Event.sync_from_stripe_data(deepcopy(FAKE_EVENT_TRANSFER_CREATED))

        self.assertEqual("<type={type}, stripe_id={stripe_id}>".format(
            type=FAKE_EVENT_TRANSFER_CREATED["type"],
            stripe_id=FAKE_EVENT_TRANSFER_CREATED["id"]
        ), str(event))

    @patch('djstripe.models.EventProcessingException.log')
    @patch('stripe.Event.retrieve')
    def test_stripe_error(self, event_retrieve_mock, event_exception_log_mock):
        fake_event_data = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
        event_retrieve_mock.return_value = fake_event_data

        event = Event.sync_from_stripe_data(fake_event_data)

        event.validate()
        event.process()

        self.assertTrue(event_exception_log_mock.called)
        self.assertFalse(event.processed)
