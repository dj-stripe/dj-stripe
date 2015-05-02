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
        # AssertionError: '<IOError, pk=1, Event=ping - evt_xxxxxxxxxxxxx>' != '<Error in transmisssion., pk=1, Event=ping - evt_xxxxxxxxxxxxx>'
        # - <IOError, pk=1, Event=ping - evt_xxxxxxxxxxxxx>
        # ?  --
        # + <Error in transmisssion., pk=1, Event=ping - evt_xxxxxxxxxxxxx>
        # ?       ++++++++++++++++++

        try:
            raise IOError("Error in transmisssion.")
        except IOError as error:
            EventProcessingException.log(data=self.msg["data"], exception=error, event=self.event)
            exception = EventProcessingException.objects.get(event=self.event)

        self.assertIn('<Error in transmisssion., pk=1, Event=ping - evt_xxxxxxxxxxxxx>', str(exception))

    def test_non_crud_link_customer_on_non_customer(self):
        self.assertEqual(None, self.event.link_customer())

    def test_non_crud_link_customer_on_invalid_customer(self):
        event_copy = deepcopy(self.event)
        event_copy.validated_message = self.invalid_customer_msg
        event_copy.save()
        self.assertEqual(None, event_copy.link_customer())
