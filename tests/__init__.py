from django.conf import settings
from stripe.resource import convert_to_stripe_object


def convert_to_fake_stripe_object(response):
    return convert_to_stripe_object(resp=response, api_key=settings.STRIPE_SECRET_KEY, account="test_account")

# Connected Stripe Object fakes.


class ChargeDict(dict):

    def refund(self, amount=None):
        self.update({"refunded": True, "amount_refunded": amount})
        return self

    def capture(self):
        self.update({"captured": True})
        return self


FAKE_CHARGE = ChargeDict({
    "id": "ch_16YKQi2eZvKYlo2CrCuzbJQx",
    "object": "charge",
    "created": 1439229084,
    "livemode": False,
    "paid": True,
    "status": "succeeded",
    "amount": 2200,
    "currency": "usd",
    "refunded": False,
    "source": {
        "id": "card_16YKQh2eZvKYlo2Cblc5Feoo",
        "object": "card",
        "last4": "4242",
        "brand": "Visa",
        "fingerprint": "dgs89-3jjf039jejda-0j2d",
        "funding": "credit",
        "exp_month": 2,
        "exp_year": 2016,
        "country": "US",
        "name": None,
        "address_line1": None,
        "address_line2": None,
        "address_city": None,
        "address_state": None,
        "address_zip": None,
        "address_country": None,
        "cvc_check": "pass",
        "address_line1_check": None,
        "address_zip_check": None,
        "tokenization_method": None,
        "dynamic_last4": None,
        "metadata": {},
        "customer": "cus_6lsBvm5rJ0zyHc"
    },
    "captured": True,
    "balance_transaction": "txn_16Vswu2eZvKYlo2C9DlWEgM1",
    "failure_message": None,
    "failure_code": None,
    "amount_refunded": 0,
    "customer": "cus_6lsBvm5rJ0zyHc",
    "invoice": "in_7udnik28sj829dj",
    "description": "VideoDoc consultation for ivanp0001 berkp0001",
    "dispute": None,
    "metadata": {},
    "statement_descriptor": None,
    "fraud_details": {},
    "receipt_email": None,
    "receipt_number": None,
    "shipping": None,
    "destination": None,
    "application_fee": None,
    "refunds": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/charges/ch_16YKQi2eZvKYlo2CrCuzbJQx/refunds",
        "data": []
    }
})


FAKE_REFUND = {
    "id": "re_16YJLj2eZvKYlo2CqZM3NdZ8",
    "amount": 1999,
    "currency": "usd",
    "created": 1439224931,
    "object": "refund",
    "balance_transaction": None,
    "metadata": {},
    "charge": "ch_16Vm0n2eZvKYlo2C34QFbOLJ",
    "receipt_number": None,
    "reason": None
}

FAKE_CUSTOMER = {
    "object": "customer",
    "created": 1439229084,
    "id": "cus_6lsBvm5rJ0zyHc",
    "livemode": False,
    "description": None,
    "email": "virtumedix+ivanp0001@gmail.com",
    "delinquent": False,
    "metadata": {},
    "subscriptions": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/customers/cus_6lsBvm5rJ0zyHc/subscriptions",
        "data": []
    },
    "discount": None,
    "account_balance": 0,
    "currency": "usd",
    "sources": {
        "object": "list",
        "total_count": 1,
        "has_more": False,
        "url": "/v1/customers/cus_6lsBvm5rJ0zyHc/sources",
        "data": [
            {
                "id": "card_16YKQh2eZvKYlo2Cblc5Feoo",
                "object": "card",
                "last4": "4242",
                "brand": "Visa",
                "funding": "credit",
                "exp_month": 2,
                "exp_year": 2016,
                "country": "US",
                "name": None,
                "address_line1": None,
                "address_line2": None,
                "address_city": None,
                "address_state": None,
                "address_zip": None,
                "address_country": None,
                "cvc_check": "pass",
                "address_line1_check": None,
                "address_zip_check": None,
                "tokenization_method": None,
                "dynamic_last4": None,
                "metadata": {
                },
                "customer": "cus_6lsBvm5rJ0zyHc"
            }
        ]
    },
    "default_source": "card_16YKQh2eZvKYlo2Cblc5Feoo"
}

FAKE_CARD = {
    "id": "card_16YKQs2eZvKYlo2C9sTYWuJj",
    "object": "card",
    "last4": "4242",
    "brand": "Visa",
    "funding": "credit",
    "exp_month": 12,
    "exp_year": 2015,
    "country": "US",
    "name": "alex-nesnes@hotmail.fr",
    "address_line1": None,
    "address_line2": None,
    "address_city": None,
    "address_state": None,
    "address_zip": None,
    "address_country": None,
    "cvc_check": "pass",
    "address_line1_check": None,
    "address_zip_check": None,
    "tokenization_method": None,
    "dynamic_last4": None,
    "metadata": {},
    "customer": None
}

FAKE_SUBSCRIPTION = {
    "id": "sub_6lsC8pt7IcFpjA",
    "plan": {
        "interval": "month",
        "name": "New plan name",
        "created": 1386247539,
        "amount": 2000,
        "currency": "usd",
        "id": "gold21323",
        "object": "plan",
        "livemode": False,
        "interval_count": 1,
        "trial_period_days": None,
        "metadata": {},
        "statement_descriptor": None
    },
    "object": "subscription",
    "start": 1439229181,
    "status": "active",
    "customer": "cus_6lsBvm5rJ0zyHc",
    "cancel_at_period_end": False,
    "current_period_start": 1439229181,
    "current_period_end": 1441907581,
    "ended_at": None,
    "trial_start": None,
    "trial_end": None,
    "canceled_at": None,
    "quantity": 1,
    "application_fee_percent": None,
    "discount": None,
    "tax_percent": None,
    "metadata": {}
}

FAKE_PLAN = {
    "interval": "month",
    "name": "New plan name",
    "created": 1386247539,
    "amount": 2000,
    "currency": "usd",
    "id": "gold21323",
    "object": "plan",
    "livemode": False,
    "interval_count": 1,
    "trial_period_days": None,
    "metadata": {},
    "statement_descriptor": None
}

FAKE_COUPON = {
    "id": "grandfathered",
    "created": 1437556338,
    "percent_off": 24,
    "amount_off": None,
    "currency": "usd",
    "object": "coupon",
    "livemode": False,
    "duration": "forever",
    "redeem_by": None,
    "max_redemptions": None,
    "times_redeemed": 2,
    "duration_in_months": None,
    "valid": True,
    "metadata": {}
}

FAKE_DISCOUNT = {
    "coupon": {
        "id": "grandfathered",
        "created": 1437556338,
        "percent_off": 24,
        "amount_off": None,
        "currency": "usd",
        "object": "coupon",
        "livemode": False,
        "duration": "forever",
        "redeem_by": None,
        "max_redemptions": None,
        "times_redeemed": 2,
        "duration_in_months": None,
        "valid": True,
        "metadata": {}
    },
    "start": 1408104978,
    "object": "discount",
    "customer": "cus_6lsBvm5rJ0zyHc",
    "subscription": "sub_4avT2dbwKJA3EL",
    "end": None
}


class InvoiceDict(dict):
    def pay(self):
        return "fish"


FAKE_INVOICE = InvoiceDict({
    "date": 1439218864,
    "id": "in_16YHls2eZvKYlo2CwwH968Mc",
    "period_start": 1439132289,
    "period_end": 1439218689,
    "lines": {
        "data": [
            {
                "id": "sub_6lsC8pt7IcFpjA",
                "object": "line_item",
                "type": "subscription",
                "livemode": True,
                "amount": 2000,
                "currency": "usd",
                "proration": False,
                "period": {
                    "start": 1441907581,
                    "end": 1444499581
                },
                "subscription": None,
                "quantity": 1,
                "plan": {
                    "interval": "month",
                    "name": "New plan name",
                    "created": 1386247539,
                    "amount": 2000,
                    "currency": "usd",
                    "id": "gold21323",
                    "object": "plan",
                    "livemode": False,
                    "interval_count": 1,
                    "trial_period_days": None,
                    "metadata": {},
                    "statement_descriptor": None
                },
                "description": None,
                "discountable": True,
                "metadata": {
                }
            }
        ],
        "total_count": 1,
        "object": "list",
        "url": "/v1/invoices/in_16YHls2eZvKYlo2CwwH968Mc/lines"
    },
    "subtotal": 2000,
    "total": 2000,
    "customer": "cus_6lsBvm5rJ0zyHc",
    "object": "invoice",
    "attempted": True,
    "closed": True,
    "forgiven": False,
    "paid": True,
    "livemode": False,
    "attempt_count": 1,
    "amount_due": 2000,
    "currency": "usd",
    "starting_balance": 0,
    "ending_balance": 0,
    "next_payment_attempt": None,
    "webhooks_delivered_at": 1439218870,
    "charge": "ch_16YIoj2eZvKYlo2CrPdYapBH",
    "discount": None,
    "application_fee": None,
    "subscription": "sub_4Ryf0Qo0XKkQnY",
    "tax_percent": None,
    "tax": None,
    "metadata": {},
    "statement_descriptor": None,
    "description": None,
    "receipt_number": None,
})

FAKE_INVOICEITEM = {
    "object": "invoiceitem",
    "id": "ii_16XVTY2eZvKYlo2Cxz5n3RaS",
    "date": 1439033216,
    "amount": 2000,
    "livemode": False,
    "proration": False,
    "currency": "usd",
    "customer": "cus_6lsBvm5rJ0zyHc",
    "discountable": True,
    "description": "One-time setup fee",
    "metadata": {
        "key1": "value1",
        "key2": "value2"
    },
    "invoice": None,
    "subscription": None,
    "quantity": None,
    "plan": None,
    "period": {
        "start": 1439033216,
        "end": 1439033216
    }
}

FAKE_DISPUTE = {
    "id": "dp_15RsQX2eZvKYlo2C0MFNUWJC",
    "charge": "ch_15RsQR2eZvKYlo2CA8IfzCX0",
    "amount": 195,
    "created": 1422915137,
    "status": "lost",
    "livemode": False,
    "currency": "usd",
    "object": "dispute",
    "reason": "general",
    "is_charge_refundable": False,
    "balance_transactions": [
        {
            "id": "txn_15RsQX2eZvKYlo2CUTLzmHcJ",
            "object": "balance_transaction",
            "amount": -195,
            "currency": "usd",
            "net": -1695,
            "type": "adjustment",
            "created": 1422915137,
            "available_on": 1423440000,
            "status": "available",
            "fee": 1500,
            "fee_details": [
                {
                    "amount": 1500,
                    "currency": "usd",
                    "type": "stripe_fee",
                    "description": "Dispute fee",
                    "application": None
                }
            ],
            "source": "ch_15RsQR2eZvKYlo2CA8IfzCX0",
            "description": "Chargeback withdrawal for ch_15RsQR2eZvKYlo2CA8IfzCX0",
            "sourced_transfers": {
                "object": "list",
                "total_count": 0,
                "has_more": False,
                "url": "/v1/transfers?source_transaction=ad_15RsQX2eZvKYlo2CYlUxjQ32",
                "data": []
            }
        }
    ],
    "evidence_details": {
        "due_by": 1424303999,
        "past_due": False,
        "has_evidence": False,
        "submission_count": 0
    },
    "evidence": {
        "product_description": None,
        "customer_name": None,
        "customer_email_address": None,
        "customer_purchase_ip": None,
        "customer_signature": None,
        "billing_address": None,
        "receipt": None,
        "shipping_address": None,
        "shipping_date": None,
        "shipping_carrier": None,
        "shipping_tracking_number": None,
        "shipping_documentation": None,
        "access_activity_log": None,
        "service_date": None,
        "service_documentation": None,
        "duplicate_charge_id": None,
        "duplicate_charge_explanation": None,
        "duplicate_charge_documentation": None,
        "refund_policy": None,
        "refund_policy_disclosure": None,
        "refund_refusal_explanation": None,
        "cancellation_policy": None,
        "cancellation_policy_disclosure": None,
        "cancellation_rebuttal": None,
        "customer_communication": None,
        "uncategorized_text": None,
        "uncategorized_file": None
    },
    "metadata": {}
}

FAKE_TRANSFER = {
    "id": "tr_16Y9BK2eZvKYlo2CR0ySu1BA",
    "object": "transfer",
    "created": 1439185846,
    "date": 1439185846,
    "livemode": False,
    "amount": 100,
    "currency": "usd",
    "reversed": False,
    "status": "paid",
    "type": "stripe_account",
    "reversals": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/transfers/tr_16Y9BK2eZvKYlo2CR0ySu1BA/reversals",
        "data": []
    },
    "balance_transaction": "txn_16Vswu2eZvKYlo2C9DlWEgM1",
    "destination": "acct_16Y9B9Fso9hLaeLu",
    "destination_payment": "py_16Y9BKFso9hLaeLueFmWAYUi",
    "description": "Test description - 1439185984",
    "failure_message": None,
    "failure_code": None,
    "amount_reversed": 0,
    "metadata": {},
    "statement_descriptor": None,
    "recipient": None,
    "source_transaction": None,
    "application_fee": None
}
FAKE_TRANSFER_REVERSAL = {
    "id": "trr_103B0z2eZvKYlo2CaV3bKTMx",
    "amount": 1880,
    "currency": "usd",
    "created": 1387829133,
    "object": "transfer_reversal",
    "balance_transaction": "txn_103B0z2eZvKYlo2CPqgXjXDI",
    "metadata": {},
    "transfer": "tr_103B0z2eZvKYlo2CI9WMGvlV"
}

FAKE_RECIPIENT = {
    "id": "rp_16UUrf2eZvKYlo2CGTJxYjum",
    "object": "recipient",
    "created": 1438315883,
    "livemode": False,
    "type": "individual",
    "description": "A Desc",
    "email": "email2@2.com",
    "name": "Bob2 Jones2",
    "verified": True,
    "metadata": {},
    "active_account": {
        "object": "bank_account",
        "id": "ba_16UUrc2eZvKYlo2CXJpDcffn",
        "last4": "6789",
        "country": "US",
        "currency": "usd",
        "status": "new",
        "fingerprint": "j1CvuuIQNXSIdZuK",
        "routing_number": "111000025",
        "bank_name": "BANK OF AMERICA, N.A."
    },
    "cards": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/recipients/rp_16UUrf2eZvKYlo2CGTJxYjum/cards",
        "data": []
    },
    "default_card": None,
    "migrated_to": None
}

FAKE_BANK_ACCOUNT = {
    "object": "bank_account",
    "id": "ba_16YKSI2eZvKYlo2C5Gi4GZJF",
    "last4": "6789",
    "country": "US",
    "currency": "usd",
    "status": "new",
    "fingerprint": "1JWtPxqbdX5Gamtc",
    "routing_number": "110000000",
    "bank_name": "STRIPE TEST BANK",
    "account": "acct_1032D82eZvKYlo2C",
    "default_for_currency": False,
    "metadata": {}
}

FAKE_APPLICATION_FEE = {
    "id": "fee_6lsCldw61KoYD2",
    "object": "application_fee",
    "created": 1439229182,
    "livemode": False,
    "amount": 100,
    "currency": "usd",
    "refunded": False,
    "amount_refunded": 0,
    "refunds": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/application_fees/fee_6lsCldw61KoYD2/refunds",
        "data": []
    },
    "balance_transaction": "txn_16Vswu2eZvKYlo2C9DlWEgM1",
    "account": "acct_1032D82eZvKYlo2C",
    "application": "ca_6lsCbngMi6c27iDAWJUW0cQkr8u9VtTa",
    "charge": "ch_16YKQi2eZvKYlo2CrCuzbJQx",
    "originating_transaction": None
}

FAKE_APPLICATION_FEE_REVERSAL = {
    "id": "fr_6lsCBm3XbQH0EN",
    "amount": 100,
    "currency": "usd",
    "created": 1439229182,
    "object": "fee_refund",
    "balance_transaction": None,
    "metadata": {},
    "fee": "fee_6lsCldw61KoYD2"
}

FAKE_ACCOUNT = {
    "id": "acct_1032D82eZvKYlo2C",
    "email": "site@stripe.com",
    "statement_descriptor": None,
    "display_name": "Stripe.com",
    "timezone": "US/Pacific",
    "details_submitted": False,
    "charges_enabled": False,
    "transfers_enabled": False,
    "currencies_supported": [
        "usd",
        "aed",
        "afn",
    ],
    "default_currency": "usd",
    "country": "US",
    "object": "account",
    "business_name": "Stripe.com",
    "business_url": None,
    "support_phone": None,
    "business_logo": None,
    "managed": False,
    "product_description": None,
    "debit_negative_balances": True,
    "bank_accounts": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/accounts/acct_1032D82eZvKYlo2C/bank_accounts",
        "data": []
    },
    "external_accounts": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/accounts/acct_1032D82eZvKYlo2C/external_accounts",
        "data": []
    },
    "verification": {
        "fields_needed": [],
        "due_by": None,
        "disabled_reason": "other"
    },
    "transfer_schedule": {
        "delay_days": 7,
        "interval": "daily"
    },
    "decline_charge_on": {
        "cvc_failure": False,
        "avs_failure": False
    },
    "tos_acceptance": {
        "ip": None,
        "date": None,
        "user_agent": None
    },
    "legal_entity": {
        "type": None,
        "business_name": None,
        "address": {
            "line1": None,
            "line2": None,
            "city": None,
            "state": None,
            "postal_code": None,
            "country": "US"
        },
        "first_name": None,
        "last_name": None,
        "personal_address": {
            "line1": None,
            "line2": None,
            "city": None,
            "state": None,
            "postal_code": None,
            "country": None
        },
        "dob": {
            "day": None,
            "month": None,
            "year": None
        },
        "additional_owners": None,
        "verification": {
            "status": "unverified",
            "document": None,
            "details": None
        }
    }
}

FAKE_BALANCE = {
    "pending": [
        {
            "amount": 75519026,
            "currency": "usd"
        }
    ],
    "available": [
        {
            "amount": 4680041949,
            "currency": "usd"
        }
    ],
    "livemode": False,
    "object": "balance"
}

FAKE_BALANCE_TRANSACTION = {
    "id": "txn_16Vswu2eZvKYlo2C9DlWEgM1",
    "object": "balance_transaction",
    "amount": 4995,
    "currency": "usd",
    "net": 4820,
    "type": "charge",
    "created": 1438646792,
    "available_on": 1439251200,
    "status": "pending",
    "fee": 175,
    "fee_details": [
        {
            "amount": 175,
            "currency": "usd",
            "type": "stripe_fee",
            "description": "Stripe processing fees",
            "application": None
        }
    ],
    "source": "ch_16Vswu2eZvKYlo2CnrIx0i3L",
    "description": "Charge for RelyMD consultation for Rakesh Mohan",
    "sourced_transfers": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/transfers?source_transaction=ch_16Vswu2eZvKYlo2CnrIx0i3L",
        "data": []
    }
}

FAKE_EVENT_CHARGE_SUCCEEDED = {
    "id": "evt_16YKQi2eZvKYlo2CT2oe5ff3",
    "created": 1439229084,
    "livemode": False,
    "type": "charge.succeeded",
    "data": {
        "object": FAKE_CHARGE
    },
    "object": "event",
    "pending_webhooks": 0,
    "request": "req_6lsB7hkicwhaDj",
    "api_version": "2015-07-28"
}

FAKE_TOKEN = {
    "id": "tok_16YDIe2eZvKYlo2CPvqprIJd",
    "livemode": False,
    "created": 1439201676,
    "used": False,
    "object": "token",
    "type": "card",
    "card": {
        "id": "card_16YDIe2eZvKYlo2CjfYJvFTk",
        "object": "card",
        "last4": "4242",
        "brand": "Visa",
        "funding": "credit",
        "exp_month": 8,
        "exp_year": 2016,
        "country": "US",
        "name": None,
        "address_line1": None,
        "address_line2": None,
        "address_city": None,
        "address_state": None,
        "address_zip": None,
        "address_country": None,
        "cvc_check": None,
        "address_line1_check": None,
        "address_zip_check": None,
        "tokenization_method": None,
        "dynamic_last4": None,
        "metadata": {}
    },
    "client_ip": None
}

FAKE_BITCOIN_RECEIVER = {
    "id": "btcrcv_16Y9hY2eZvKYlo2CLsYPSJqt",
    "object": "bitcoin_receiver",
    "created": 1439187844,
    "livemode": False,
    "active": True,
    "amount": 2000,
    "amount_received": 2000,
    "bitcoin_amount": 20000000,
    "bitcoin_amount_received": 20000000,
    "bitcoin_uri": "bitcoin:test_TI6fc7RLQuBhNs9AZ2Z7RgmLFpvMT?amount=0.20000000",
    "currency": "usd",
    "filled": True,
    "inbound_address": "test_TI6fc7RLQuBhNs9AZ2Z7RgmLFpvMT",
    "uncaptured_funds": True,
    "description": "Donate to Developers",
    "email": "1337alexpham@gmail.com",
    "metadata": {},
    "refund_address": None
}

TEST_FILE_UPLOAD = {
    "id": "fil_15A3Gj2eZvKYlo2C0NxXGm4s",
    "created": 1418666909,
    "size": 1529506,
    "purpose": "dispute_evidence",
    "object": "file_upload",
    "type": "pdf"
}
