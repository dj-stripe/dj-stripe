"""
.. module:: dj-stripe.tests.__init__
   :synopsis: dj-stripe test fakes

.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

A Fake or multiple fakes for each stripe object.

Originally collected using API VERSION 2015-07-28.
Updated to API VERSION 2016-03-07 with bogus fields.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from copy import deepcopy
from datetime import datetime

from django.utils import timezone, dateformat

from djstripe.webhooks import TEST_EVENT_ID

FUTURE_DATE = datetime(2100, 4, 30, tzinfo=timezone.utc)


def datetime_to_unix(datetime_):
    return int(dateformat.format(datetime_, 'U'))


class StripeList(dict):
    object = "list"
    has_more = False
    url = "/v1/fakes"

    def __init__(self, data):
        self.data = data

    def __getitem__(self, key):
        return self.getattr(key)

    def auto_paging_iter(self):
        return self.data

    @property
    def total_count(self):
        return len(self.data)


def default_account():
    from djstripe.models import Account
    return Account.objects.create(
        charges_enabled=True, details_submitted=True, payouts_enabled=True
    )


FAKE_BALANCE_TRANSACTION = {
    "id": "txn_16YKQi2eZvKYlo2CNx26h2Wz",
    "object": "balance_transaction",
    "amount": 3340,
    "available_on": 1439769600,
    "created": 1439229084,
    "currency": "usd",
    "description": "Charge for RelyMD consultation for Rakesh Mohan",
    "fee": 127,
    "fee_details": [
        {
            "amount": 127,
            "currency": "usd",
            "type": "stripe_fee",
            "description": "Stripe processing fees",
            "application": None,
        }
    ],
    "net": 3213,
    "source": "ch_16YKQi2eZvKYlo2CrCuzbJQx",
    "sourced_transfers": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/transfers?source_transaction=ch_16YKQi2eZvKYlo2CrCuzbJQx",
        "data": []
    },
    "status": "pending",
    "type": "charge",
}

FAKE_BALANCE_TRANSACTION_II = {
    "id": "txn_16g5h62eZvKYlo2CQ2AHA89s",
    "object": "balance_transaction",
    "amount": 65400,
    "available_on": 1441670400,
    "created": 1441079064,
    "currency": "usd",
    "description": None,
    "fee": 1927,
    "fee_details": [
        {
          "amount": 1927,
          "currency": "usd",
          "type": "stripe_fee",
          "description": "Stripe processing fees",
          "application": None,
        }
    ],
    "net": 63473,
    "source": "ch_16g5h62eZvKYlo2CMRXkSqa0",
    "sourced_transfers": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/transfers?source_transaction=ch_16g5h62eZvKYlo2CMRXkSqa0",
        "data": [],
    },
    "status": "pending",
    "type": "charge",
}

FAKE_BALANCE_TRANSACTION_III = {
    "id": "txn_16g5h62eZvKYlo2CQ2AHA89s",
    "object": "balance_transaction",
    "amount": 2000,
    "available_on": 1441670400,
    "created": 1441079064,
    "currency": "usd",
    "description": None,
    "fee": 1927,
    "fee_details": [
        {
          "amount": 1927,
          "currency": "usd",
          "type": "stripe_fee",
          "description": "Stripe processing fees",
          "application": None,
        }
    ],
    "net": 73,
    "source": "ch_16g5h62eZvKYlo2CMRXkSqa0",
    "sourced_transfers": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/transfers?source_transaction=ch_16g5h62eZvKYlo2CMRXkSqa0",
        "data": [],
    },
    "status": "pending",
    "type": "charge",
}

FAKE_BALANCE_TRANSACTION_IV = {
    "id": "txn_16g5h62eZvKYlo2CQ2AHA89s",
    "object": "balance_transaction",
    "amount": 19010,
    "available_on": 1441670400,
    "created": 1441079064,
    "currency": "usd",
    "description": None,
    "fee": 1927,
    "fee_details": [
        {
          "amount": 1927,
          "currency": "usd",
          "type": "stripe_fee",
          "description": "Stripe processing fees",
          "application": None,
        }
    ],
    "net": 17083,
    "source": "ch_16g5h62eZvKYlo2CMRXkSqa0",
    "sourced_transfers": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/transfers?source_transaction=ch_16g5h62eZvKYlo2CMRXkSqa0",
        "data": [],
    },
    "status": "pending",
    "type": "charge",
}

FAKE_BANK_ACCOUNT = {
    "id": "ba_16hTzo2eZvKYlo2CeSjfb0tS",
    "object": "bank_account",
    "account_holder_name": None,
    "account_holder_type": None,
    "bank_name": "STRIPE TEST BANK",
    "country": "US",
    "currency": "usd",
    "fingerprint": "1JWtPxqbdX5Gamtc",
    "last4": "6789",
    "routing_number": "110000000",
    "status": "new",
}

FAKE_BANK_ACCOUNT_II = {
    "id": "ba_17O4Tz2eZvKYlo2CMYsxroV5",
    "object": "bank_account",
    "account_holder_name": None,
    "account_holder_type": None,
    "bank_name": None,
    "country": "US",
    "currency": "usd",
    "fingerprint": "1JWtPxqbdX5Gamtc",
    "last4": "6789",
    "routing_number": "110000000",
    "status": "new",
}


class CardDict(dict):

    def delete(self):
        return self


FAKE_CARD = CardDict({
    "id": "card_16YKQh2eZvKYlo2Cblc5Feoo",
    "object": "card",
    "address_city": None,
    "address_country": None,
    "address_line1": None,
    "address_line1_check": None,
    "address_line2": None,
    "address_state": None,
    "address_zip": None,
    "address_zip_check": None,
    "brand": "Visa",
    "country": "US",
    "customer": "cus_6lsBvm5rJ0zyHc",
    "cvc_check": "pass",
    "dynamic_last4": None,
    "exp_month": 12,
    "exp_year": 2016,
    "funding": "credit",
    "last4": "4242",
    "metadata": {},
    "name": "alex-nesnes@hotmail.fr",
    "tokenization_method": None,
})

FAKE_CARD_II = CardDict({
    "id": "card_14Lc4K2eZvKYlo2CcXyAXlDR",
    "object": "card",
    "address_city": None,
    "address_country": None,
    "address_line1": None,
    "address_line1_check": None,
    "address_line2": None,
    "address_state": None,
    "address_zip": None,
    "address_zip_check": None,
    "brand": "Visa",
    "country": "US",
    "customer": "cus_4UbFSo9tl62jqj",
    "cvc_check": None,
    "dynamic_last4": None,
    "exp_month": 7,
    "exp_year": 2015,
    "fingerprint": "Xt5EWLLDS7FJjR1c",
    "funding": "credit",
    "last4": "4242",
    "metadata": {},
    "name": None,
    "tokenization_method": None,
})

FAKE_CARD_III = CardDict({
    "id": "card_17PLiR2eZvKYlo2CRwTCUAdZ",
    "object": "card",
    "address_city": None,
    "address_country": None,
    "address_line1": None,
    "address_line1_check": None,
    "address_line2": None,
    "address_state": None,
    "address_zip": None,
    "address_zip_check": None,
    "brand": "American Express",
    "country": "US",
    "customer": None,
    "cvc_check": "unchecked",
    "dynamic_last4": None,
    "exp_month": 7,
    "exp_year": 2019,
    "fingerprint": "Xt5EWLLDS7FJjR1c",
    "funding": "credit",
    "last4": "1005",
    "metadata": {},
    "name": None,
    "tokenization_method": None,
})

FAKE_CARD_IV = CardDict({
    "id": "card_186Qdm2eZvKYlo2CInjNRrRE",
    "object": "card",
    "address_city": None,
    "address_country": None,
    "address_line1": None,
    "address_line1_check": None,
    "address_line2": None,
    "address_state": None,
    "address_zip": None,
    "address_zip_check": None,
    "brand": "Visa",
    "country": "US",
    "customer": None,
    "cvc_check": "unchecked",
    "dynamic_last4": None,
    "exp_month": 6,
    "exp_year": 2018,
    "funding": "credit",
    "last4": "4242",
    "metadata": {},
    "name": None,
    "tokenization_method": None,
})

FAKE_CARD_V = CardDict({
    "id": "card_16YKQh2eZeZvKYlo2CInFeoo",
    "object": "card",
    "address_city": None,
    "address_country": None,
    "address_line1": None,
    "address_line1_check": None,
    "address_line2": None,
    "address_state": None,
    "address_zip": None,
    "address_zip_check": None,
    "brand": "Visa",
    "country": "US",
    "customer": "cus_6lsBvm5rJ0zyHc",
    "cvc_check": "pass",
    "dynamic_last4": None,
    "exp_month": 5,
    "exp_year": 2015,
    "funding": "credit",
    "last4": "4242",
    "metadata": {},
    "name": None,
    "tokenization_method": None,
})


class ChargeDict(dict):

    def refund(self, amount=None, reason=None):
        self.update({"refunded": True, "amount_refunded": amount})
        return self

    def capture(self):
        self.update({"captured": True})
        return self


FAKE_CHARGE = ChargeDict({
    "id": "ch_16YKQi2eZvKYlo2CrCuzbJQx",
    "object": "charge",
    "amount": 2200,
    "amount_refunded": 0,
    "application_fee": None,
    "balance_transaction": deepcopy(FAKE_BALANCE_TRANSACTION),
    "captured": True,
    "created": 1439229084,
    "currency": "usd",
    "customer": "cus_6lsBvm5rJ0zyHc",
    "description": "VideoDoc consultation for ivanp0001 berkp0001",
    "destination": None,
    "dispute": None,
    "failure_code": None,
    "failure_message": None,
    "fraud_details": {},
    "invoice": "in_7udnik28sj829dj",
    "livemode": False,
    "metadata": {},
    "order": None,
    "outcome": {
        "network_status": "approved_by_network",
        "reason": None,
        "risk_level": "normal",
        "seller_message": "Payment complete.",
        "type": "authorized",
    },
    "paid": True,
    "receipt_email": None,
    "receipt_number": None,
    "refunded": False,
    "refunds": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/charges/ch_16YKQi2eZvKYlo2CrCuzbJQx/refunds",
        "data": []
    },
    "shipping": None,
    "source": deepcopy(FAKE_CARD),
    "source_transfer": None,
    "statement_descriptor": None,
    "status": "succeeded",
})

FAKE_CHARGE_II = ChargeDict({
    "id": "ch_16ag432eZvKYlo2CGDe6lvVs",
    "object": "charge",
    "amount": 3000,
    "amount_refunded": 0,
    "application_fee": None,
    "balance_transaction": deepcopy(FAKE_BALANCE_TRANSACTION),
    "captured": False,
    "created": 1439788903,
    "currency": "usd",
    "customer": "cus_4UbFSo9tl62jqj",
    "description": None,
    "destination": None,
    "dispute": None,
    "failure_code": "expired_card",
    "failure_message": "Your card has expired.",
    "fraud_details": {},
    "invoice": "in_16af5A2eZvKYlo2CJjANLL81",
    "livemode": False,
    "metadata": {},
    "order": None,
    "outcome": {
        "network_status": "declined_by_network",
        "reason": "expired_card",
        "risk_level": "normal",
        "seller_message": "The bank returned the decline code `expired_card`.",
        "type": "issuer_declined",
    },
    "paid": False,
    "receipt_email": None,
    "receipt_number": None,
    "refunded": False,
    "refunds": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/charges/ch_16ag432eZvKYlo2CGDe6lvVs/refunds",
        "data": [],
    },
    "shipping": None,
    "source": deepcopy(FAKE_CARD_II),
    "source_transfer": None,
    "statement_descriptor": None,
    "status": "failed",
})


FAKE_COUPON = {
    "id": "fake-coupon-1",
    "object": "coupon",
    "amount_off": None,
    "created": 1490157071,
    "currency": None,
    "duration": "once",
    "duration_in_months": None,
    "livemode": False,
    "max_redemptions": None,
    "metadata": {},
    "percent_off": 1,
    "redeem_by": None,
    "times_redeemed": 0,
    "valid": True,
}


FAKE_DISPUTE = {
    "id": "dp_XXXXXXXXXXXXXXXXXXXXXXXX",
    "object": "dispute",
    "amount": 499,
    "balance_transaction": FAKE_BALANCE_TRANSACTION_III["id"],
    "balance_transactions": [deepcopy(FAKE_BALANCE_TRANSACTION_III)],
    "charge": FAKE_CHARGE["id"],
    "created": 1515012086,
    "currency": "usd",
    "evidence": {
      "access_activity_log": None,
      "billing_address": None,
      "cancellation_policy": None,
      "cancellation_policy_disclosure": None,
      "cancellation_rebuttal": None,
      "customer_communication": None,
      "customer_email_address": "customer@example.com",
      "customer_name": "customer@example.com",
      "customer_purchase_ip": "127.0.0.1",
      "customer_signature": None,
      "duplicate_charge_documentation": None,
      "duplicate_charge_explanation": None,
      "duplicate_charge_id": None,
      "product_description": None,
      "receipt": "file_XXXXXXXXXXXXXXXXXXXXXXXX",
      "refund_policy": None,
      "refund_policy_disclosure": None,
      "refund_refusal_explanation": None,
      "service_date": None,
      "service_documentation": None,
      "shipping_address": None,
      "shipping_carrier": None,
      "shipping_date": None,
      "shipping_documentation": None,
      "shipping_tracking_number": None,
      "uncategorized_file": None,
      "uncategorized_text": None,
    },
    "evidence_details": {
      "due_by": 1516406399,
      "has_evidence": False,
      "past_due": False,
      "submission_count": 0,
    },
    "is_charge_refundable": False,
    "livemode": True,
    "metadata": {},
    "reason": "subscription_canceled",
    "status": "needs_response",
}


FAKE_PLAN = {
    "id": "gold21323",
    "object": "plan",
    "amount": 2000,
    "created": 1386247539,
    "currency": "usd",
    "interval": "month",
    "interval_count": 1,
    "livemode": False,
    "metadata": {},
    "name": "New plan name",
    "statement_descriptor": None,
    "trial_period_days": None,
    "usage_type": "licensed",
}

FAKE_PLAN_II = {
    "id": "silver41294",
    "object": "plan",
    "amount": 4000,
    "created": 1386247539,
    "currency": "usd",
    "interval": "week",
    "interval_count": 1,
    "livemode": False,
    "metadata": {},
    "name": "New plan name",
    "statement_descriptor": None,
    "trial_period_days": 12,
    "usage_type": "licensed",
}

FAKE_TIER_PLAN = {
    "id": "tier21323",
    "object": "plan",
    "amount": None,
    "created": 1386247539,
    "currency": "usd",
    "interval": "month",
    "interval_count": 1,
    "livemode": False,
    "metadata": {},
    "name": "New plan name",
    "statement_descriptor": None,
    "trial_period_days": None,
    "usage_type": "licensed",
    "tiers_mode": "graduated",
    "tiers": [
        {
            "flat_amount": 4900,
            "unit_amount": 1000,
            "up_to": 5
        },
        {
            "flat_amount": "null",
            "unit_amount": 900,
            "up_to": None
        },
    ]
}


class SubscriptionDict(dict):

    def __setattr__(self, name, value):
        if type(value) == datetime:
            value = datetime_to_unix(value)

        # Special case for plan
        if name == "plan":
            for plan in [FAKE_PLAN, FAKE_PLAN_II]:
                if value == plan["id"]:
                    value = plan

        self[name] = value

    def delete(self, **kwargs):
        if "at_period_end" in kwargs:
            self["cancel_at_period_end"] = kwargs["at_period_end"]

        return self

    def save(self, idempotency_key=None):
        return self


FAKE_SUBSCRIPTION = SubscriptionDict({
    "id": "sub_6lsC8pt7IcFpjA",
    "object": "subscription",
    "application_fee_percent": None,
    "billing": "charge_automatically",
    "cancel_at_period_end": False,
    "canceled_at": None,
    "current_period_end": 1441907581,
    "current_period_start": 1439229181,
    "customer": "cus_6lsBvm5rJ0zyHc",
    "discount": None,
    "ended_at": None,
    "metadata": {},
    "plan": deepcopy(FAKE_PLAN),
    "quantity": 1,
    "start": 1439229181,
    "status": "active",
    "tax_percent": None,
    "trial_end": None,
    "trial_start": None,
})

FAKE_SUBSCRIPTION_CANCELED = deepcopy(FAKE_SUBSCRIPTION)
FAKE_SUBSCRIPTION_CANCELED["status"] = "canceled"
FAKE_SUBSCRIPTION_CANCELED["canceled_at"] = 1440907580

FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END = deepcopy(FAKE_SUBSCRIPTION)
FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END["canceled_at"] = 1440907580
FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END["cancel_at_period_end"] = True

FAKE_SUBSCRIPTION_II = SubscriptionDict({
    "id": "sub_6mkwMbhaZF9jih",
    "object": "subscription",
    "application_fee_percent": None,
    "billing": "charge_automatically",
    "cancel_at_period_end": False,
    "canceled_at": None,
    "current_period_end": 1442111228,
    "current_period_start": 1439432828,
    "customer": "cus_6lsBvm5rJ0zyHc",
    "discount": None,
    "ended_at": None,
    "metadata": {},
    "plan": deepcopy(FAKE_PLAN_II),
    "quantity": 1,
    "start": 1386247539,
    "status": "active",
    "tax_percent": None,
    "trial_end": None,
    "trial_start": None,
})

FAKE_SUBSCRIPTION_III = SubscriptionDict({
    "id": "sub_8NDptncNY485qZ",
    "object": "subscription",
    "application_fee_percent": None,
    "billing": "charge_automatically",
    "cancel_at_period_end": False,
    "canceled_at": None,
    "current_period_end": 1464821382,
    "current_period_start": 1462142982,
    "customer": "cus_4UbFSo9tl62jqj",
    "discount": None,
    "ended_at": None,
    "metadata": {},
    "plan": deepcopy(FAKE_PLAN),
    "quantity": 1,
    "start": 1462142982,
    "status": "active",
    "tax_percent": None,
    "trial_end": None,
    "trial_start": None,
})


class Sources(object):

    def __init__(self, card_fakes):
        self.card_fakes = card_fakes

    def create(self, source, api_key=None):
        for fake_card in self.card_fakes:
            if fake_card["id"] == source:
                return fake_card

    def retrieve(self, id, expand=None):  # noqa
        for fake_card in self.card_fakes:
            if fake_card["id"] == id:
                return fake_card

    def list(self, **kwargs):
        return StripeList(data=self.card_fakes)


class CustomerDict(dict):
    def save(self, idempotency_key=None):
        return self

    def delete(self):
        return self

    @property
    def sources(self):
        return Sources(card_fakes=self["sources"]["data"])

    def create_for_user(self, user):
        from djstripe.models import Customer
        stripe_customer = Customer.sync_from_stripe_data(self)
        stripe_customer.subscriber = user
        stripe_customer.save()
        return stripe_customer


FAKE_CUSTOMER = CustomerDict({
    "id": "cus_6lsBvm5rJ0zyHc",
    "object": "customer",
    "account_balance": 0,
    "created": 1439229084,
    "currency": "usd",
    "default_source": deepcopy(FAKE_CARD),
    "delinquent": False,
    "description": "Michael Smith",
    "discount": None,
    "email": "michael.smith@example.com",
    "livemode": False,
    "metadata": {},
    "shipping": None,
    "sources": {
        "object": "list",
        "total_count": 2,
        "has_more": False,
        "url": "/v1/customers/cus_6lsBvm5rJ0zyHc/sources",
        "data": [deepcopy(FAKE_CARD), deepcopy(FAKE_CARD_V)]
    },
    "subscriptions": {
        "object": "list",
        "total_count": 2,
        "has_more": False,
        "url": "/v1/customers/cus_6lsBvm5rJ0zyHc/subscriptions",
        "data": [deepcopy(FAKE_SUBSCRIPTION), deepcopy(FAKE_SUBSCRIPTION_II)]
    },
})


FAKE_CUSTOMER_II = CustomerDict({
    "id": "cus_4UbFSo9tl62jqj",
    "object": "customer",
    "account_balance": 0,
    "created": 1439229084,
    "currency": "usd",
    "default_source": deepcopy(FAKE_CARD_II),
    "delinquent": False,
    "description": "John Snow",
    "discount": None,
    "email": "john.snow@thewall.com",
    "livemode": False,
    "metadata": {},
    "shipping": None,
    "sources": {
        "object": "list",
        "total_count": 1,
        "has_more": False,
        "url": "/v1/customers/cus_4UbFSo9tl62jqj/sources",
        "data": [deepcopy(FAKE_CARD_II)]
    },
    "subscriptions": {
        "object": "list",
        "total_count": 1,
        "has_more": False,
        "url": "/v1/customers/cus_4UbFSo9tl62jqj/subscriptions",
        "data": [deepcopy(FAKE_SUBSCRIPTION_III)]
    },
})


FAKE_DISCOUNT_CUSTOMER = {
    "object": "discount",
    "coupon": deepcopy(FAKE_COUPON),
    "customer": FAKE_CUSTOMER["id"],
    "start": 1493206114,
    "end": None,
    "subscription": None,
}


class InvoiceDict(dict):
    def pay(self):
        return self


FAKE_INVOICE = InvoiceDict({
    "id": "in_16YHls2eZvKYlo2CwwH968Mc",
    "object": "invoice",
    "amount_due": 2000,
    "amount_paid": 2000,
    "amount_remaining": 0,
    "application_fee": None,
    "attempt_count": 1,
    "attempted": True,
    "billing": "charge_automatically",
    "charge": FAKE_CHARGE["id"],
    "closed": True,
    "currency": "usd",
    "customer": "cus_6lsBvm5rJ0zyHc",
    "date": 1439218864,
    "description": None,
    "discount": None,
    "due_date": None,
    "ending_balance": 0,
    "forgiven": False,
    "lines": {
        "data": [
            {
                "id": FAKE_SUBSCRIPTION["id"],
                "object": "line_item",
                "amount": 2000,
                "currency": "usd",
                "description": None,
                "discountable": True,
                "livemode": True,
                "metadata": {},
                "period": {
                    "start": 1441907581,
                    "end": 1444499581
                },
                "plan": deepcopy(FAKE_PLAN),
                "proration": False,
                "quantity": 1,
                "subscription": None,
                "type": "subscription",
            }
        ],
        "total_count": 1,
        "object": "list",
        "url": "/v1/invoices/in_16YHls2eZvKYlo2CwwH968Mc/lines",
    },
    "livemode": False,
    "metadata": {},
    "next_payment_attempt": None,
    "number": "XXXXXXX-0001",
    "paid": True,
    "period_end": 1439218689,
    "period_start": 1439132289,
    "receipt_number": None,
    "starting_balance": 0,
    "statement_descriptor": None,
    "subscription": FAKE_SUBSCRIPTION["id"],
    "subtotal": 2000,
    "tax": None,
    "tax_percent": None,
    "total": 2000,
    "webhooks_delivered_at": 1439218870,
})

FAKE_INVOICE_II = InvoiceDict({
    "id": "in_16af5A2eZvKYlo2CJjANLL81",
    "object": "invoice",
    "amount_due": 3000,
    "amount_paid": 0,
    "amount_remaining": 3000,
    "application_fee": None,
    "attempt_count": 1,
    "attempted": True,
    "billing": "charge_automatically",
    "charge": FAKE_CHARGE_II["id"],
    "closed": False,
    "currency": "usd",
    "customer": "cus_4UbFSo9tl62jqj",
    "date": 1439785128,
    "description": None,
    "discount": None,
    "due_date": None,
    "ending_balance": 0,
    "forgiven": False,
    "lines": {
        "data": [
            {
                "id": FAKE_SUBSCRIPTION_III["id"],
                "object": "line_item",
                "amount": 2000,
                "currency": "usd",
                "description": None,
                "discountable": True,
                "livemode": True,
                "metadata": {},
                "period": {
                    "start": 1442469907,
                    "end": 1445061907
                },
                "plan": deepcopy(FAKE_PLAN),
                "proration": False,
                "quantity": 1,
                "subscription": None,
                "type": "subscription",
            }
        ],
        "total_count": 1,
        "object": "list",
        "url": "/v1/invoices/in_16af5A2eZvKYlo2CJjANLL81/lines",
    },
    "livemode": False,
    "metadata": {},
    "next_payment_attempt": 1440048103,
    "number": "XXXXXXX-0002",
    "paid": False,
    "period_end": 1439784771,
    "period_start": 1439698371,
    "receipt_number": None,
    "starting_balance": 0,
    "statement_descriptor": None,
    "subscription": FAKE_SUBSCRIPTION_III["id"],
    "subtotal": 3000,
    "tax": None,
    "tax_percent": None,
    "total": 3000,
    "webhooks_delivered_at": 1439785139,
})


FAKE_INVOICE_III = InvoiceDict({
    "id": "in_16Z9dP2eZvKYlo2CgFHgFx2Z",
    "object": "invoice",
    "amount_due": 0,
    "amount_paid": 0,
    "amount_remaining": 0,
    "application_fee": None,
    "attempt_count": 0,
    "attempted": True,
    "billing": "charge_automatically",
    "charge": None,
    "closed": False,
    "currency": "usd",
    "customer": "cus_6lsBvm5rJ0zyHc",
    "date": 1439425915,
    "description": None,
    "discount": None,
    "due_date": None,
    "ending_balance": 20,
    "forgiven": False,
    "lines": {
        "data": [
            {
                "id": FAKE_SUBSCRIPTION["id"],
                "object": "line_item",
                "amount": 2000,
                "currency": "usd",
                "description": None,
                "discountable": True,
                "livemode": True,
                "metadata": {},
                "period": {
                    "start": 1442111228,
                    "end": 1444703228
                },
                "plan": deepcopy(FAKE_PLAN),
                "proration": False,
                "quantity": 1,
                "subscription": None,
                "type": "subscription",
            }
        ],
        "total_count": 1,
        "object": "list",
        "url": "/v1/invoices/in_16Z9dP2eZvKYlo2CgFHgFx2Z/lines",
    },
    "livemode": False,
    "metadata": {},
    "next_payment_attempt": None,
    "number": "XXXXXXX-0003",
    "paid": False,
    "period_end": 1439424571,
    "period_start": 1436746171,
    "receipt_number": None,
    "starting_balance": 0,
    "statement_descriptor": None,
    "subscription": FAKE_SUBSCRIPTION["id"],
    "subtotal": 20,
    "tax": None,
    "tax_percent": None,
    "total": 20,
    "webhooks_delivered_at": 1439426955,
})

FAKE_UPCOMING_INVOICE = InvoiceDict({
    "id": "in",
    "object": "invoice",
    "amount_due": 2000,
    "amount_paid": 0,
    "amount_remaining": 2000,
    "application_fee": None,
    "attempt_count": 1,
    "attempted": False,
    "billing": "charge_automatically",
    "charge": None,
    "closed": False,
    "currency": "usd",
    "customer": FAKE_CUSTOMER["id"],
    "date": 1439218864,
    "description": None,
    "discount": None,
    "due_date": None,
    "ending_balance": None,
    "forgiven": False,
    "lines": {
        "data": [
            {
                "id": FAKE_SUBSCRIPTION["id"],
                "object": "line_item",
                "amount": 2000,
                "currency": "usd",
                "description": None,
                "discountable": True,
                "livemode": True,
                "metadata": {},
                "period": {
                    "start": 1441907581,
                    "end": 1444499581
                },
                "plan": deepcopy(FAKE_PLAN),
                "proration": False,
                "quantity": 1,
                "subscription": None,
                "type": "subscription",
            }
        ],
        "total_count": 1,
        "object": "list",
        "url": "/v1/invoices/in_16YHls2eZvKYlo2CwwH968Mc/lines",
    },
    "livemode": False,
    "metadata": {},
    "next_payment_attempt": 1439218689,
    "number": None,
    "paid": False,
    "period_end": 1439218689,
    "period_start": 1439132289,
    "receipt_number": None,
    "starting_balance": 0,
    "statement_descriptor": None,
    "subscription": FAKE_SUBSCRIPTION["id"],
    "subtotal": 2000,
    "tax": None,
    "tax_percent": None,
    "total": 2000,
    "webhooks_delivered_at": 1439218870,
})

FAKE_INVOICEITEM = {
    "id": "ii_16XVTY2eZvKYlo2Cxz5n3RaS",
    "object": "invoiceitem",
    "amount": 2000,
    "currency": "usd",
    "customer": FAKE_CUSTOMER_II["id"],
    "date": 1439033216,
    "description": "One-time setup fee",
    "discountable": True,
    "invoice": FAKE_INVOICE_II["id"],
    "livemode": False,
    "metadata": {
        "key1": "value1",
        "key2": "value2"
    },
    "period": {
        "start": 1439033216,
        "end": 1439033216,
    },
    "plan": None,
    "proration": False,
    "quantity": None,
    "subscription": None,
}

FAKE_INVOICEITEM_II = {
    "id": "ii_16XVTY2eZvKYlo2Cxz5n3RaS",
    "object": "invoiceitem",
    "amount": 2000,
    "currency": "usd",
    "customer": FAKE_CUSTOMER["id"],
    "date": 1439033216,
    "description": "One-time setup fee",
    "discountable": True,
    "invoice": FAKE_INVOICE["id"],
    "livemode": False,
    "metadata": {
        "key1": "value1",
        "key2": "value2"
    },
    "period": {
        "start": 1439033216,
        "end": 1439033216,
    },
    "plan": None,
    "proration": False,
    "quantity": None,
    "subscription": None,
}

FAKE_TRANSFER = {
    "id": "tr_16Y9BK2eZvKYlo2CR0ySu1BA",
    "object": "transfer",
    "amount": 100,
    "amount_reversed": 0,
    "application_fee": None,
    "balance_transaction": deepcopy(FAKE_BALANCE_TRANSACTION_II),
    "created": 1439185846,
    "currency": "usd",
    "date": 1439185846,
    "description": "Test description - 1439185984",
    "destination": "acct_16Y9B9Fso9hLaeLu",
    "destination_payment": "py_16Y9BKFso9hLaeLueFmWAYUi",
    "failure_code": None,
    "failure_message": None,
    "livemode": False,
    "metadata": {},
    "recipient": None,
    "reversals": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/transfers/tr_16Y9BK2eZvKYlo2CR0ySu1BA/reversals",
        "data": [],
    },
    "reversed": False,
    "source_transaction": None,
    "source_type": "bank_account",
    "statement_descriptor": None,
    "status": "paid",
}

FAKE_TRANSFER_II = {
    "id": "tr_16hTzv2eZvKYlo2CWuyMmuvV",
    "object": "transfer",
    "amount": 2000,
    "amount_reversed": 0,
    "application_fee": None,
    "balance_transaction": deepcopy(FAKE_BALANCE_TRANSACTION_III),
    "bank_account": deepcopy(FAKE_BANK_ACCOUNT),
    "created": 1440420000,
    "currency": "usd",
    "date": 1440420000,
    "description": None,
    "destination": "ba_16hTzo2eZvKYlo2CeSjfb0tS",
    "failure_code": None,
    "failure_message": None,
    "livemode": False,
    "metadata": {
        "foo": "bar",
    },
    "recipient": "rp_16hTzu2eZvKYlo2C9A5mgxEj",
    "reversals": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/transfers/tr_16hTzv2eZvKYlo2CWuyMmuvV/reversals",
        "data": [],
    },
    "reversed": False,
    "source_transaction": None,
    "source_type": "card",
    "statement_descriptor": None,
    "status": "paid",
    "type": "bank_account",
}

FAKE_TRANSFER_III = {
    "id": "tr_17O4U52eZvKYlo2CmyYbDAEy",
    "object": "transfer",
    "amount": 19010,
    "amount_reversed": 0,
    "application_fee": None,
    "balance_transaction": deepcopy(FAKE_BALANCE_TRANSACTION_IV),
    "bank_account": deepcopy(FAKE_BANK_ACCOUNT_II),
    "created": 1451560845,
    "currency": "usd",
    "date": 1451560845,
    "description": "Transfer+for+test@example.com",
    "destination": "ba_17O4Tz2eZvKYlo2CMYsxroV5",
    "failure_code": None,
    "failure_message": None,
    "livemode": False,
    "metadata": {
        "foo2": "bar2",
    },
    "recipient": "rp_17O4U42eZvKYlo2CLk4upfDE",
    "reversals": {
        "object": "list",
        "total_count": 0,
        "has_more": False,
        "url": "/v1/transfers/tr_17O4U52eZvKYlo2CmyYbDAEy/reversals",
        "data": [],
    },
    "reversed": False,
    "source_transaction": None,
    "source_type": "card",
    "statement_descriptor": None,
    "status": "paid",
    "type": "bank_account",
}

FAKE_ACCOUNT = {
    "id": "acct_1032D82eZvKYlo2C",
    "object": "account",
    "business_logo": None,
    "business_name": "dj-stripe",
    "business_primary_color": "#092e20",
    "business_url": "https://example.com",
    "charges_enabled": True,
    "country": "US",
    "default_currency": "usd",
    "details_submitted": True,
    "display_name": "dj-stripe",
    "email": "djstripe@example.com",
    "payouts_enabled": True,
    "statement_descriptor": "DJSTRIPE",
    "support_email": "djstripe@example.com",
    "support_phone": None,
    "support_url": "https://example.com/support/",
    "timezone": "Etc/UTC",
    "type": "standard",
}

FAKE_EVENT_ACCOUNT_APPLICATION_DEAUTHORIZED = {
    "id": "evt_XXXXXXXXXXXXXXXXXXXXXXXX",
    "type": "account.application.deauthorized",
    "pending_webhooks": 0,
    "livemode": False,
    "request": None,
    "api_version": None,
    "created": 1493823371,
    "object": "event",
    "data": {
        "object": {
            "id": "ca_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "object": "application",
            "name": "Test Connect Application",
        }
    },
}

# 2017-05-25 api changed request from id to object with id and idempotency_key
# issue #541
FAKE_EVENT_PLAN_REQUEST_IS_OBJECT = {
    "id": "evt_1AcdbXXXXXXXXXXXXXXXXXXX",
    "object": "event",
    "api_version": "2017-06-05",
    "created": 1499361420,
    "data": {
        "object": FAKE_PLAN,
        "previous_attributes": {
            "name": "Plan anual test4"
        }
    },
    "livemode": False,
    "pending_webhooks": 1,
    "request": {
        "id": "req_AyamqQWoi5AMR2",
        "idempotency_key": None,
    },
    "type": "plan.updated",
}

FAKE_EVENT_CHARGE_SUCCEEDED = {
    "id": "evt_16YKQi2eZvKYlo2CT2oe5ff3",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1439229084,
    "data": {
        "object": deepcopy(FAKE_CHARGE)
    },
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6lsB7hkicwhaDj",
    "type": "charge.succeeded",
}

FAKE_EVENT_TEST_CHARGE_SUCCEEDED = deepcopy(FAKE_EVENT_CHARGE_SUCCEEDED)
FAKE_EVENT_TEST_CHARGE_SUCCEEDED['id'] = TEST_EVENT_ID

FAKE_EVENT_CUSTOMER_CREATED = {
    "id": "evt_38DHch3whaDvKYlo2CT2oe5ff3",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1439229084,
    "data": {
        "object": deepcopy(FAKE_CUSTOMER)
    },
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6l38DHch3whaDj",
    "type": "customer.created",
}

FAKE_EVENT_CUSTOMER_DELETED = deepcopy(FAKE_EVENT_CUSTOMER_CREATED)
FAKE_EVENT_CUSTOMER_DELETED.update({
    "id": "evt_38DHch3whaDvKYlo2jksfsFFxy",
    "type": "customer.deleted"
})

FAKE_EVENT_CUSTOMER_DISCOUNT_CREATED = {
    "id": "AGBWvF5zBm4sMCsLLPZrw9XX",
    "type": "customer.discount.created",
    "api_version": "2017-02-14",
    "created": 1439229084,
    "object": "discount",
    "pending_webhooks": 0,
    "request": "req_6l38DHch3whaDj",
    "data": {
        "object": deepcopy(FAKE_DISCOUNT_CUSTOMER),
    }
}

FAKE_EVENT_CUSTOMER_DISCOUNT_DELETED = {
    "id": "AGBWvF5zBm4sMCsLLPZrw9XX",
    "type": "customer.discount.deleted",
    "api_version": "2017-02-14",
    "created": 1439229084,
    "object": "discount",
    "pending_webhooks": 0,
    "request": "req_6l38DHch3whaDj",
    "data": {
        "object": deepcopy(FAKE_DISCOUNT_CUSTOMER),
    }
}

FAKE_EVENT_CUSTOMER_SOURCE_CREATED = {
    "id": "evt_DvKYlo38huDvKYlo2C7SXedrZk",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1439229084,
    "data": {
        "object": deepcopy(FAKE_CARD)
    },
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_o3whaDvh3whaDj",
    "type": "customer.source.created",
}

FAKE_EVENT_CUSTOMER_SOURCE_DELETED = deepcopy(FAKE_EVENT_CUSTOMER_SOURCE_CREATED)
FAKE_EVENT_CUSTOMER_SOURCE_DELETED.update({
    "id": "evt_DvKYlo38huDvKYlo2C7SXedrYk",
    "type": "customer.source.deleted"
})

FAKE_EVENT_CUSTOMER_SOURCE_DELETED_DUPE = deepcopy(FAKE_EVENT_CUSTOMER_SOURCE_DELETED)
FAKE_EVENT_CUSTOMER_SOURCE_DELETED_DUPE.update({
    "id": "evt_DvKYlo38huDvKYlo2C7SXedzAk",
})

FAKE_EVENT_CUSTOMER_SUBSCRIPTION_CREATED = {
    "id": "evt_38DHch3wHD2eZvKYlCT2oe5ff3",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1439229084,
    "data": {
        "object": deepcopy(FAKE_SUBSCRIPTION)
    },
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6l87IHch3diaDj",
    "type": "customer.subscription.created",
}

FAKE_EVENT_CUSTOMER_SUBSCRIPTION_DELETED = deepcopy(FAKE_EVENT_CUSTOMER_SUBSCRIPTION_CREATED)
FAKE_EVENT_CUSTOMER_SUBSCRIPTION_DELETED.update({
    "id": "evt_38DHch3wHD2eZvKYlCT2oeryaf",
    "type": "customer.subscription.deleted"})

FAKE_EVENT_DISPUTE_CREATED = {
    "id": "evt_16YKQi2eZvKYlo2CT2oe5ff3",
    "object": "dispute",
    "api_version": "2017-08-15",
    "created": 1439229084,
    "data": {
        "object": deepcopy(FAKE_DISPUTE)
    },
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6lsB7hkicwhaDj",
    "type": "charge.dispute.created",
}

FAKE_EVENT_INVOICE_CREATED = {
    "id": "evt_187IHD2eZvKYlo2C6YKQi2eZ",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1462338623,
    "data": {
        "object": deepcopy(FAKE_INVOICE)
    },
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_8O4sB7hkDobVT",
    "type": "invoice.created",
}

FAKE_EVENT_INVOICE_DELETED = deepcopy(FAKE_EVENT_INVOICE_CREATED)
FAKE_EVENT_INVOICE_DELETED.update({
    "id": "evt_187IHD2eZvKYlo2Cjkjsr34H",
    "type": "invoice.deleted"})

FAKE_EVENT_INVOICE_UPCOMING = {
    "id": "evt_187IHD2eZvKYlo2C6YKQi2bc",
    "object": "event",
    "api_version": "2017-02-14",
    "created": 1501859641,
    "data": {
        "object": deepcopy(FAKE_INVOICE)
    },
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_8O4sB7hkDobZA",
    "type": "invoice.upcoming",
}
del FAKE_EVENT_INVOICE_UPCOMING["data"]["object"]["id"]


FAKE_EVENT_INVOICEITEM_CREATED = {
    "id": "evt_187IHD2eZvKYlo2C7SXedrZk",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1462338623,
    "data": {
        "object": deepcopy(FAKE_INVOICEITEM)
    },
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_8O4Qbs2EDobDVT",
    "type": "invoiceitem.created",
}

FAKE_EVENT_INVOICEITEM_DELETED = deepcopy(FAKE_EVENT_INVOICEITEM_CREATED)
FAKE_EVENT_INVOICEITEM_DELETED.update({
    "id": "evt_187IHD2eZvKYloJfdsnnfs34",
    "type": "invoiceitem.deleted"})

FAKE_EVENT_PLAN_CREATED = {
    "id": "evt_1877X72eZvKYlo2CLK6daFxu",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1462297325,
    "data": {
        "object": deepcopy(FAKE_PLAN)
    },
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_8NtJXPttxSvFyM",
    "type": "plan.created",
}

FAKE_EVENT_PLAN_DELETED = deepcopy(FAKE_EVENT_PLAN_CREATED)
FAKE_EVENT_PLAN_DELETED.update({
    "id": "evt_1877X72eZvKYl2jkds32jJFc",
    "type": "plan.deleted"})

FAKE_EVENT_TRANSFER_CREATED = {
    "id": "evt_16igNU2eZvKYlo2CYyMkYvet",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1441696732,
    "data": {
        "object": deepcopy(FAKE_TRANSFER)
    },
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6wZW9MskhYU15Y",
    "type": "transfer.created",
}

FAKE_EVENT_TRANSFER_DELETED = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
FAKE_EVENT_TRANSFER_DELETED.update({
    "id": "evt_16igNU2eZvKjklfsdjk232Mf",
    "type": "transfer.deleted"})

FAKE_TOKEN = {
    "id": "tok_16YDIe2eZvKYlo2CPvqprIJd",
    "object": "token",
    "card": deepcopy(FAKE_CARD),
    "client_ip": None,
    "created": 1439201676,
    "livemode": False,
    "type": "card",
    "used": False,
}
