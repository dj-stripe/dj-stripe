"""
.. module:: dj-stripe.tests.test_event
   :synopsis: dj-stripe Event Model Tests.

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from mock import patch, PropertyMock
import stripe

from djstripe.models import Customer, Event, Subscription
from tests import convert_to_fake_stripe_object


class EventTest(TestCase):
    message = {
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
                "id": "cus_yyyyyyyyyyyyyyyyyyyy",
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

    fake_current_subscription = Subscription(stripe_id="sub_yyyyyyyyyyyyyy",
                                             plan="test",
                                             quantity=1,
                                             start=timezone.now(),
                                             amount=Decimal(25.00))

    def setUp(self):
        self.message["data"]["object"]["customer"] = "cus_xxxxxxxxxxxxxxx"  # Yes, this is intentional.

        self.user = get_user_model().objects.create_user(username="testuser",
                                                         email="testuser@gmail.com")
        self.customer = Customer.objects.create(
            stripe_id=self.message["data"]["object"]["customer"],
            subscriber=self.user
        )

    def test_tostring(self):
        event = Event.objects.create(
            stripe_id=self.message["id"],
            kind="eventkind",
            webhook_message=self.message,
            validated_message=self.message,
            valid=True
        )
        self.assertEquals("<eventkind, stripe_id=evt_xxxxxxxxxxxxx>", str(event))

    def test_link_customer_customer_created(self):
        msg = {
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
            "type": "customer.created"
        }
        event = Event.objects.create(
            stripe_id=msg["id"],
            kind="customer.created",
            livemode=True,
            webhook_message=msg,
            validated_message=msg
        )
        event.link_customer()
        self.assertEquals(event.customer, self.customer)

    def test_link_customer_customer_updated(self):
        msg = {
            "created": 1346855599,
            "data": {
                "object": {
                    "account_balance": 0,
                    "active_card": {
                        "address_city": None,
                        "address_country": None,
                        "address_line1": None,
                        "address_line1_check": None,
                        "address_line2": None,
                        "address_state": None,
                        "address_zip": None,
                        "address_zip_check": None,
                        "country": "MX",
                        "cvc_check": "pass",
                        "exp_month": 1,
                        "exp_year": 2014,
                        "fingerprint": "XXXXXXXXXXX",
                        "last4": "7992",
                        "name": None,
                        "object": "card",
                        "type": "MasterCard"
                    },
                    "created": 1346855596,
                    "delinquent": False,
                    "description": None,
                    "discount": None,
                    "email": "xxxxxxxxxx@yahoo.com",
                    "id": "cus_xxxxxxxxxxxxxxx",
                    "livemode": True,
                    "object": "customer",
                    "subscription": None
                },
                "previous_attributes": {
                    "active_card": None
                }
            },
            "id": "evt_xxxxxxxxxxxxx",
            "livemode": True,
            "object": "event",
            "pending_webhooks": 1,
            "type": "customer.updated"
        }
        event = Event.objects.create(
            stripe_id=msg["id"],
            kind="customer.updated",
            livemode=True,
            webhook_message=msg,
            validated_message=msg
        )
        event.link_customer()
        self.assertEquals(event.customer, self.customer)

    def test_link_customer_customer_deleted(self):
        msg = {
            "created": 1348286560,
            "data": {
                "object": {
                    "account_balance": 0,
                    "active_card": None,
                    "created": 1348286302,
                    "delinquent": False,
                    "description": None,
                    "discount": None,
                    "email": "paltman+test@gmail.com",
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
            "type": "customer.deleted"
        }
        event = Event.objects.create(
            stripe_id=msg["id"],
            kind="customer.deleted",
            livemode=True,
            webhook_message=msg,
            validated_message=msg
        )
        event.link_customer()
        self.assertEquals(event.customer, self.customer)

    @patch('stripe.Event.retrieve', return_value=convert_to_fake_stripe_object({"data": message["data"], "zebra": True, "alpha": False}))
    def test_validate_true(self, event_retrieve_mock):
        event = Event.objects.create(
            stripe_id=self.message["id"],
            kind="ping",
            webhook_message=self.message,
            validated_message=self.message
        )

        self.assertEqual(None, event.valid)
        event.validate()
        event_retrieve_mock.assert_called_once_with(self.message["id"])
        self.assertEqual(True, event.valid)

    @patch('stripe.Event.retrieve', return_value=convert_to_fake_stripe_object({"data": {"object": {"flavor": "chocolate"}}, "zebra": True, "alpha": False}))
    def test_validate_false(self, event_retrieve_mock):
        event = Event.objects.create(
            stripe_id=self.message["id"],
            kind="ping",
            webhook_message=self.message,
            validated_message=self.message
        )

        self.assertEqual(None, event.valid)
        event.validate()
        event_retrieve_mock.assert_called_once_with(self.message["id"])
        self.assertEqual(False, event.valid)

    def test_process_exit_immediately(self):
        event = Event.objects.create(
            stripe_id=self.message["id"],
            kind="ping",
            webhook_message=self.message,
            validated_message=self.message,
            valid=False
        )

        event.process()
        self.assertFalse(event.processed)

    @patch('stripe.Invoice.retrieve')
    @patch('djstripe.models.Invoice.sync_from_stripe_data')
    def test_process_invoice_event(self, stripe_sync_mock, retrieve_mock):
        event = Event.objects.create(
            stripe_id=self.message["id"],
            kind="invoice.created",
            webhook_message=self.message,
            validated_message=self.message,
            valid=True
        )
        event.process()
        retrieve_mock.assert_called_once_with(self.message['data']['object']['id'])
        self.assertTrue(event.processed)

    @patch('djstripe.models.Customer.record_charge')
    def test_process_charge_event(self, record_charge_mock):
        event = Event.objects.create(
            stripe_id=self.message["id"],
            kind="charge.created",
            webhook_message=self.message,
            validated_message=self.message,
            valid=True
        )

        event.process()
        self.assertEqual(event.customer, self.customer)
        record_charge_mock.assert_called_once_with(self.message["data"]["object"]["id"])
        self.assertTrue(event.processed)

    @patch('djstripe.models.Customer.sync_current_subscription')
    def test_customer_subscription_event(self, sync_current_subscription_mock):
        event = Event.objects.create(
            stripe_id=self.message["id"],
            kind="customer.subscription.created",
            webhook_message=self.message,
            validated_message=self.message,
            valid=True
        )

        event.process()
        sync_current_subscription_mock.assert_called_once_with()
        self.assertTrue(event.processed)

    @patch('djstripe.models.Customer.sync_subscriptions')
    def test_customer_multiple_subscription_event(self, sync_subscriptions_mock):
        event = Event.objects.create(
            stripe_id=self.message["id"],
            kind="customer.subscription.created",
            webhook_message=self.message,
            validated_message=self.message,
            valid=True
        )
        
        Customer.allow_multiple_subscriptions = True
        event.process()
        Customer.allow_multiple_subscriptions = False
        sync_subscriptions_mock.assert_called_once_with()
        self.assertTrue(event.processed)
        
    @patch('djstripe.models.Customer.sync_current_subscription')
    def test_customer_subscription_event_no_customer(self, sync_current_subscription_mock):
        self.message["data"]["object"]["customer"] = None
        event = Event.objects.create(
            stripe_id=self.message["id"],
            kind="customer.subscription.created",
            webhook_message=self.message,
            validated_message=self.message,
            valid=True
        )

        event.process()
        self.assertFalse(sync_current_subscription_mock.called)
        self.assertTrue(event.processed)

    @patch("djstripe.models.Customer.current_subscription", new_callable=PropertyMock, return_value=fake_current_subscription)
    def test_customer_subscription_deleted_event(self, current_subscription_mock):
        event = Event.objects.create(
            stripe_id=self.message["id"],
            kind="customer.subscription.deleted",
            webhook_message=self.message,
            validated_message=self.message,
            valid=True
        )

        event.process()
        self.assertTrue(current_subscription_mock.status, Subscription.STATUS_CANCELLED)
        self.assertTrue(event.processed)

    @patch("stripe.Customer.retrieve")
    def test_process_customer_deleted(self, customer_retrieve_mock):
        msg = {
            "created": 1348286560,
            "data": {
                "object": {
                    "account_balance": 0,
                    "active_card": None,
                    "created": 1348286302,
                    "delinquent": False,
                    "description": None,
                    "discount": None,
                    "email": "paltman+test@gmail.com",
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
            "type": "customer.deleted"
        }
        event = Event.objects.create(
            stripe_id=msg["id"],
            kind="customer.deleted",
            livemode=True,
            webhook_message=msg,
            validated_message=msg,
            valid=True
        )
        event.process()
        self.assertEquals(event.customer, self.customer)
        self.assertEquals(event.customer.subscriber, None)
        self.assertTrue(event.processed)

    def test_invalid_event_kind(self):
        """Should just fail silently and not do anything."""
        event = Event.objects.create(
            stripe_id=self.message["id"],
            kind="fake.event.kind",
            webhook_message=self.message,
            validated_message=self.message,
            valid=True
        )

        event.process()
        self.assertTrue(event.processed)

    @patch('djstripe.models.EventProcessingException.log')
    @patch('djstripe.models.Event.send_signal', side_effect=stripe.StripeError())
    def test_stripe_error(self, send_signal_mock, event_exception_log):
        event = Event.objects.create(
            stripe_id=self.message["id"],
            kind="fake.event.kind",
            webhook_message=self.message,
            validated_message=self.message,
            valid=True
        )

        event.process()
        self.assertTrue(event_exception_log.called)
        self.assertFalse(event.processed)
