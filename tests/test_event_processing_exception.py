"""
.. module:: dj-stripe.tests.test_event_processing_exception
   :synopsis: dj-stripe EventProcessingException Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy

from django.test import TestCase

from djstripe.models import EventProcessingException, Event


class TestEventProcessingException(TestCase):

    def setUp(self):
        self.msg = {
            "created": 1363911708,
            "data": {
                "object": {
                    "account_balance": 0,
                    "active_card": None,
                    "created": 1363911708,
                    "delinquent": False,
                    "description": None,
                    "discount": None,
                    "email": "xxxxxxxxxx@yahoo.com",
                    "id": "cus_xxxxxxxxxxxxxxx",
                    "livemode": True,
                    "object": "customer",
                    "subscription": None
                }
            },
            "id": "evt_xxxxxxxxxxxxx",
            "livemode": True,
            "object": "event",
            "pending_webhooks": 1,
            "type": "ping"
        }

        self.invalid_customer_msg = {
            "created": 1363911708,
            "data": {
                "object": {
                    "account_balance": 0,
                    "active_card": None,
                    "created": 1363911708,
                    "delinquent": False,
                    "description": None,
                    "discount": None,
                    "email": "xxxxxxxxxx@yahoo.com",
                    "customer": "cus_xxxxxxxxxxxxxxx",
                    "livemode": True,
                    "object": "customer",
                    "subscription": None
                }
            },
            "id": "evt_xxxxxxxxxxxxx",
            "livemode": True,
            "object": "event",
            "pending_webhooks": 1,
            "type": "ping"
        }

        self.event = Event.objects.create(
            stripe_id=self.msg["id"],
            kind="ping",
            webhook_message=self.msg,
            validated_message=self.msg
        )

    def test_tostring(self):
        # Not sure if this is normal, but self.exception returns:
        # AssertionError: '<IOError, pk=1, Event=ping - evt_xxxxxxxxxxxxx>' != '<Error in transmission., pk=1, Event=ping - evt_xxxxxxxxxxxxx>'
        # - <IOError, pk=1, Event=ping - evt_xxxxxxxxxxxxx>
        # ?  --
        # + <Error in transmission., pk=1, Event=<ping, stripe_id=evt_xxxxxxxxxxxxx>>
        # ?       ++++++++++++++++++

        try:
            raise IOError("Error in transmission.")
        except IOError as error:
            EventProcessingException.log(data=self.msg["data"], exception=error, event=self.event)
            exception = EventProcessingException.objects.get(event=self.event)

        # It may be too strict to assert the pk? Maybe incr field not reset in some psql implementations?
        # self.assertIn('<Error in transmission., pk=1, Event=<ping, stripe_id=evt_xxxxxxxxxxxxx>>', str(exception))
        self.assertIn('<Error in transmission., pk=', str(exception))
        self.assertIn(', Event=<ping, stripe_id=evt_xxxxxxxxxxxxx>>', str(exception))

    def test_non_crud_link_customer_on_non_customer(self):
        self.event.process()
        self.assertEqual(None, self.event.customer)

    def test_non_crud_link_customer_on_invalid_customer(self):
        event_copy = deepcopy(self.event)
        event_copy.validated_message = self.invalid_customer_msg
        event_copy.save()
        event_copy.process()
        self.assertEqual(None, event_copy.customer)
