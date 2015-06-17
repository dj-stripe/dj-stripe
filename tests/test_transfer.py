"""
.. module:: dj-stripe.tests.test_transfer
   :synopsis: dj-stripe Transfer Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy

from django.test.testcases import TestCase

from mock import patch, PropertyMock

from djstripe.models import Event, Transfer


TRANSFER_CREATED_TEST_DATA = {
    "created": 1348360173,
    "data": {
        "object": {
            "amount": 455,
            "currency": "usd",
            "date": 1348876800,
            "description": None,
            "id": "tr_XXXXXXXXXXXX",
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
    "id": "evt_XXXXXXXXXXXX",
    "livemode": True,
    "object": "event",
    "pending_webhooks": 1,
    "type": "transfer.created"
}

TRANSFER_CREATED_TEST_DATA2 = {
    "created": 1348360173,
    "data": {
        "object": {
            "amount": 1455,
            "currency": "usd",
            "date": 1348876800,
            "description": None,
            "id": "tr_XXXXXXXXXXX2",
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
                "charge_gross": 1500,
                "collected_fee_count": 0,
                "collected_fee_gross": 0,
                "currency": "usd",
                "net": 1455,
                "refund_count": 0,
                "refund_fees": 0,
                "refund_gross": 0,
                "validation_count": 0,
                "validation_fees": 0
            }
        }
    },
    "id": "evt_XXXXXXXXXXXY",
    "livemode": True,
    "object": "event",
    "pending_webhooks": 1,
    "type": "transfer.created"
}


class TransferTest(TestCase):

    @patch('stripe.Transfer.retrieve', return_value=PropertyMock(status="fish"))
    def test_update_transfer(self, transfer_receive_mock):
        TRANSFER_UPDATED_TEST_DATA = deepcopy(TRANSFER_CREATED_TEST_DATA)
        TRANSFER_UPDATED_TEST_DATA["type"] = "transfer.updated"
        TRANSFER_UPDATED_TEST_DATA["data"]["object"]["id"] = "salmon"

        # Create transfer
        created_event = Event.objects.create(
            stripe_id=TRANSFER_CREATED_TEST_DATA["id"],
            kind="transfer.created",
            livemode=True,
            webhook_message=TRANSFER_CREATED_TEST_DATA,
            validated_message=TRANSFER_CREATED_TEST_DATA,
            valid=True
        )
        created_event.process()

        # Signal a transfer update
        updated_event = Event.objects.create(
            stripe_id="evt_test_update",
            kind="transfer.updated",
            livemode=True,
            webhook_message=TRANSFER_UPDATED_TEST_DATA,
            validated_message=TRANSFER_UPDATED_TEST_DATA,
            valid=True
        )
        updated_event.process()

        transfer_instance = Transfer.objects.get(stripe_id="salmon")
        transfer_receive_mock.assert_called_once_with(transfer_instance.stripe_id)
        self.assertEqual(transfer_instance.status, "fish")

        # Test to string
        self.assertEquals("<amount=4.55, status=fish, stripe_id=salmon>", str(transfer_instance))
