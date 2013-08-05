import decimal
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from mock import patch

from . import TRANSFER_CREATED_TEST_DATA
from ..models import Event, Transfer


class TestWebhook(TestCase):
    
    @patch("stripe.Event.retrieve")
    def test_webhook_with_transfer_event(self, StripeEventMock):
        data = {
            "created": 1348360173,
            "data": {
                "object": {
                    "amount": 455,
                    "currency": "usd",
                    "date": 1348876800,
                    "description": None,
                    "id": "ach_XXXXXXXXXXXX",
                    "object": "transfer",
                    "other_transfers": [],
                    "status": "pending",
                    "summary": {
                        "adjustment_count": 0,
                        "adjustment_fee_details": [],
                        "adjustment_fees": 0,
                        "adjustment_gross": 0,
                        "charge_count": 1,
                        "charge_fee_details": [{
                            "amount": 45,
                            "application": None,
                            "currency": "usd",
                            "description": None,
                            "type": "stripe_fee"
                        }],
                        "charge_fees": 45,
                        "charge_gross": 500,
                        "collected_fee_count": 0,
                        "collected_fee_gross": 0,
                        "currency": "usd",
                        "net": 455,
                        "refund_count": 0,
                        "refund_fees": 0,
                        "refund_gross": 0,
                        "validation_count": 0,
                        "validation_fees": 0
                    }
                }
            },
            "id": "evt_XXXXXXXXXXXXx",
            "livemode": True,
            "object": "event",
            "pending_webhooks": 1,
            "type": "transfer.created"
        }
        StripeEventMock.return_value.to_dict.return_value = data
        msg = json.dumps(data)
        resp = Client().post(
            reverse("payments_webhook"),
            msg,
            content_type="application/json"
        )
        self.assertEquals(resp.status_code, 200)
        self.assertTrue(Event.objects.filter(kind="transfer.created").exists())


class TestTransferWebhooks(TestCase):
    
    def test_transfer_created(self):
        event = Event.objects.create(
            stripe_id=TRANSFER_CREATED_TEST_DATA["id"],
            kind="transfer.created",
            livemode=True,
            webhook_message=TRANSFER_CREATED_TEST_DATA,
            validated_message=TRANSFER_CREATED_TEST_DATA,
            valid=True
        )
        event.process()
        transfer = Transfer.objects.get(stripe_id="tr_XXXXXXXXXXXX")
        self.assertEquals(transfer.amount, decimal.Decimal("4.55"))
        self.assertEquals(transfer.status, "paid")
    
    def test_transfer_paid_updates_existing_record(self):
        event = Event.objects.create(
            stripe_id=TRANSFER_CREATED_TEST_DATA["id"],
            kind="transfer.created",
            livemode=True,
            webhook_message=TRANSFER_CREATED_TEST_DATA,
            validated_message=TRANSFER_CREATED_TEST_DATA,
            valid=True
        )
        event.process()
        data = {
            "created": 1364658818,
            "data": {
                "object": {
                    "account": {
                        "bank_name": "BANK OF AMERICA, N.A.",
                        "country": "US",
                        "last4": "9999",
                        "object": "bank_account"
                    },
                    "amount": 455,
                    "currency": "usd",
                    "date": 1364601600,
                    "description": "STRIPE TRANSFER",
                    "fee": 0,
                    "fee_details": [],
                    "id": "tr_XXXXXXXXXXXX",
                    "livemode": True,
                    "object": "transfer",
                    "other_transfers": [],
                    "status": "paid",
                    "summary": {
                        "adjustment_count": 0,
                        "adjustment_fee_details": [],
                        "adjustment_fees": 0,
                        "adjustment_gross": 0,
                        "charge_count": 1,
                        "charge_fee_details": [{
                            "amount": 45,
                            "application": None,
                            "currency": "usd",
                            "description": None,
                            "type": "stripe_fee"
                        }],
                        "charge_fees": 45,
                        "charge_gross": 500,
                        "collected_fee_count": 0,
                        "collected_fee_gross": 0,
                        "collected_fee_refund_count": 0,
                        "collected_fee_refund_gross": 0,
                        "currency": "usd",
                        "net": 455,
                        "refund_count": 0,
                        "refund_fee_details": [],
                        "refund_fees": 0,
                        "refund_gross": 0,
                        "validation_count": 0,
                        "validation_fees": 0
                    },
                    "transactions": {
                        "count": 1,
                        "data": [{
                            "amount": 500,
                            "created": 1364064631,
                            "description": None,
                            "fee": 45,
                            "fee_details": [{
                                "amount": 45,
                                "application": None,
                                "currency": "usd",
                                "description": "Stripe processing fees",
                                "type": "stripe_fee"
                            }],
                            "id": "ch_XXXXXXXXXX",
                            "net": 455,
                            "type": "charge"
                        }],
                        "object": "list",
                        "url": "/v1/transfers/XX/transactions"
                    }
                }
            },
            "id": "evt_YYYYYYYYYYYY",
            "livemode": True,
            "object": "event",
            "pending_webhooks": 1,
            "type": "transfer.paid"
        }
        paid_event = Event.objects.create(
            stripe_id=data["id"],
            kind="transfer.paid",
            livemode=True,
            webhook_message=data,
            validated_message=data,
            valid=True
        )
        paid_event.process()
        transfer = Transfer.objects.get(stripe_id="tr_XXXXXXXXXXXX")
        self.assertEquals(transfer.status, "paid")
