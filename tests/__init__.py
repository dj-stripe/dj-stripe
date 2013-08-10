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