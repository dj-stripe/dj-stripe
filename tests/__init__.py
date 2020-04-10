"""
A Fake or multiple fakes for each stripe object.

Originally collected using API VERSION 2015-07-28.
Updated to API VERSION 2016-03-07 with bogus fields.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import logging
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import dateformat, timezone

from djstripe.webhooks import TEST_EVENT_ID

logger = logging.getLogger(__name__)

FUTURE_DATE = datetime(2100, 4, 30, tzinfo=timezone.utc)

FIXTURE_DIR_PATH = Path(__file__).parent.joinpath("fixtures")


# Flags for various bugs with mock autospec
# These can be removed once we drop support for the affected python versions

# Don't try and use autospec=True on staticmethods on <py3.7
# see https://bugs.python.org/issue23078
IS_STATICMETHOD_AUTOSPEC_SUPPORTED = sys.version_info >= (3, 7, 4)


class AssertStripeFksMixin:
    def assert_fks(self, obj, expected_blank_fks, processed_stripe_ids=None):
        """
        Recursively walk through fks on obj, asserting they're not-none
        :param obj:
        :param expected_blank_fks: fields that are expected to be None
        :param processed_stripe_ids: set of objects ids already processed
        :return:
        """

        if processed_stripe_ids is None:
            processed_stripe_ids = set()

        processed_stripe_ids.add(obj.id)

        for field in obj._meta.get_fields():
            if isinstance(field, (models.ForeignKey, models.OneToOneRel)):
                if isinstance(field, models.OneToOneRel):
                    if field.parent_link:
                        # skip checking model inheritance links
                        continue

                    # Check reverse OneToOneFields
                    # Hack - there's probably a better way to generate this name?
                    reverse_id_name = str(field.remote_field.foreign_related_fields[0])
                    field_str = reverse_id_name.replace("djstripe_id", field.name)
                    field_str += " (related name)"
                else:
                    field_str = str(field)

                try:
                    field_value = getattr(obj, field.name)
                except ObjectDoesNotExist:
                    field_value = None

                if field_str in expected_blank_fks:
                    self.assertIsNone(field_value, field_str)
                else:
                    self.assertIsNotNone(field_value, field_str)

                    if field_value.id not in processed_stripe_ids:
                        # recurse into the object if it's not already been checked
                        self.assert_fks(
                            field_value, expected_blank_fks, processed_stripe_ids
                        )

                    logger.warning("checked {}".format(field_str))


def load_fixture(filename):
    with FIXTURE_DIR_PATH.joinpath(filename).open("r") as f:
        return json.load(f)


def datetime_to_unix(datetime_):
    return int(dateformat.format(datetime_, "U"))


class StripeItem(dict):
    """Flexible class built to mock any generic Stripe object.

    Implements object access + deletion methods to match the behavior
    of Stripe's library, which allows both object + dictionary access.

    Has a delete method since (most) Stripe objects can be deleted.
    """

    def __getattr__(self, name):
        """Give StripeItem normal object access to match Stripe behavior."""
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def delete(self) -> bool:
        """Superficial mock that adds a deleted attribute."""
        self.deleted = True

        return self.deleted


class StripeList(dict):
    """Mock a generic Stripe Iterable.

    It has the relevant attributes of a stripe iterable (has_more, data).

    This mock is important so we can use stripe's `list` method in our testing.
    StripeList.list() will return the StripeList.

    Additionally, iterating over instances of MockStripeIterable will iterate over
    the data attribute, just like Stripe iterables.

    Attributes:
        has_more: mock has_more flag. Default False.
        **kwargs: all of the fields of the stripe object, generally as a dictionary.
    """

    object = "list"
    url = "/v1/fakes"
    has_more = False

    def __getattr__(self, name):
        """Give StripeItem normal object access to match Stripe behavior."""
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __iter__(self) -> Any:
        """Make StripeList an iterable, to match the Stripe iterable behavior."""
        self.iter_copy = self.data.copy()
        return self

    def __next__(self) -> StripeItem:
        """Define iteration for StripeList."""
        if len(self.iter_copy) > 0:
            return self.iter_copy.pop(0)
        else:
            raise StopIteration()

    def list(self, **kwargs: Any) -> "StripeList":
        """Add a list method to the StripeList which returns itself.

        list() accepts arbitrary kwargs, be careful is you expect the
        argument-accepting functionality of Stripe's list() method.
        """
        return self

    def auto_paging_iter(self) -> "StripeList":
        """Add an auto_paging_iter method to the StripeList which returns itself.

        The StripeList is an iterable, so this mimics the real behavior.
        """
        return self

    @property
    def total_count(self):
        return len(self.data)


def default_account():
    from djstripe.models import Account

    return Account.objects.create(
        charges_enabled=True, details_submitted=True, payouts_enabled=True
    )


FAKE_BALANCE_TRANSACTION = load_fixture(
    "balance_transaction_txn_fake_ch_fakefakefakefakefake0001.json"
)

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


class LegacySourceDict(dict):
    def delete(self):
        return self


class BankAccountDict(LegacySourceDict):
    pass


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

FAKE_BANK_ACCOUNT_SOURCE = BankAccountDict(
    load_fixture("bank_account_ba_fakefakefakefakefake0003.json")
)


class CardDict(LegacySourceDict):
    pass


FAKE_CARD = CardDict(load_fixture("card_card_fakefakefakefakefake0001.json"))

FAKE_CARD_II = CardDict(load_fixture("card_card_fakefakefakefakefake0002.json"))

FAKE_CARD_III = CardDict(
    {
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
        "metadata": {"djstripe_test_fake_id": "card_fakefakefakefakefake0003"},
        "name": None,
        "tokenization_method": None,
    }
)

FAKE_CARD_IV = CardDict(
    {
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
        "metadata": {"djstripe_test_fake_id": "card_fakefakefakefakefake0004"},
        "name": None,
        "tokenization_method": None,
    }
)

FAKE_CARD_V = CardDict(load_fixture("card_card_fakefakefakefakefake0005.json"))


class SourceDict(dict):
    def detach(self):
        self.pop("customer")
        self.update({"status": "consumed"})
        return self


# Attached, chargeable source
FAKE_SOURCE = SourceDict(load_fixture("source_src_fakefakefakefakefake0001.json"))

# Detached, consumed source
FAKE_SOURCE_II = SourceDict(
    {
        "id": "src_1DuuGjkE6hxDGaasasjdlajl",
        "object": "source",
        "amount": None,
        "card": {
            "address_line1_check": None,
            "address_zip_check": "pass",
            "brand": "Visa",
            "country": "US",
            "cvc_check": "pass",
            "dynamic_last4": None,
            "exp_month": 10,
            "exp_year": 2029,
            "fingerprint": "TmOrYzPdAoO6YFNB",
            "funding": "credit",
            "last4": "4242",
            "name": None,
            "three_d_secure": "optional",
            "tokenization_method": None,
        },
        "client_secret": "src_client_secret_ENg5dyB1KTXCAEJGJQWEf67X",
        "created": 1548046215,
        "currency": None,
        "flow": "none",
        "livemode": False,
        "metadata": {"djstripe_test_fake_id": "src_fakefakefakefakefake0002"},
        "owner": {
            "address": {
                "city": None,
                "country": None,
                "line1": None,
                "line2": None,
                "postal_code": "90210",
                "state": None,
            },
            "email": None,
            "name": None,
            "phone": None,
            "verified_address": None,
            "verified_email": None,
            "verified_name": None,
            "verified_phone": None,
        },
        "statement_descriptor": None,
        "status": "consumed",
        "type": "card",
        "usage": "reusable",
    }
)


FAKE_PAYMENT_INTENT_I = load_fixture("payment_intent_pi_fakefakefakefakefake0001.json")


class PaymentMethodDict(dict):
    def detach(self):
        self.pop("customer")
        return self


FAKE_PAYMENT_METHOD_I = PaymentMethodDict(
    load_fixture("payment_method_pm_fakefakefakefake0001.json")
)

# FAKE_CARD, but accessed as a PaymentMethod
FAKE_CARD_AS_PAYMENT_METHOD = PaymentMethodDict(
    load_fixture("payment_method_card_fakefakefakefakefake0001.json")
)


# TODO - add to regenerate_test_fixtures and replace this with a JSON fixture
FAKE_SETUP_INTENT_I = {
    "id": "seti_fakefakefakefake0001",
    "object": "setup_intent",
    "cancellation_reason": None,
    "payment_method_types": ["card"],
    "status": "requires_payment_method",
    "usage": "off_session",
}


# TODO - add to regenerate_test_fixtures and replace this with a JSON fixture
#  (will need to use a different payment_intent fixture)
FAKE_SESSION_I = {
    "id": "cs_test_OAgNmy75Td25OeREvKUs8XZ7SjMPO9qAplqHO1sBaEjOg9fYbaeMh2nA",
    "object": "checkout.session",
    "billing_address_collection": None,
    "cancel_url": "https://example.com/cancel",
    "client_reference_id": None,
    "customer": "cus_6lsBvm5rJ0zyHc",
    "customer_email": None,
    "display_items": [
        {
            "amount": 1500,
            "currency": "usd",
            "custom": {
                "description": "Comfortable cotton t-shirt",
                "images": None,
                "name": "T-shirt",
            },
            "quantity": 2,
            "type": "custom",
        }
    ],
    "livemode": False,
    "locale": None,
    "mode": None,
    "payment_intent": FAKE_PAYMENT_INTENT_I["id"],
    "payment_method_types": ["card"],
    "setup_intent": None,
    "submit_type": None,
    "subscription": None,
    "success_url": "https://example.com/success",
}


class ChargeDict(StripeItem):
    def __init__(self, *args, **kwargs):
        """Match Stripe's behavior: return a stripe iterable on `charge.refunds`."""
        super().__init__(*args, **kwargs)
        self.refunds = StripeList(self.refunds)

    def refund(self, amount=None, reason=None):
        self.update({"refunded": True, "amount_refunded": amount})
        return self

    def capture(self):
        self.update({"captured": True})
        return self


FAKE_CHARGE = ChargeDict(load_fixture("charge_ch_fakefakefakefakefake0001.json"))


FAKE_CHARGE_II = ChargeDict(
    {
        "id": "ch_16ag432eZvKYlo2CGDe6lvVs",
        "object": "charge",
        "amount": 3000,
        "amount_refunded": 0,
        "application_fee": None,
        "balance_transaction": FAKE_BALANCE_TRANSACTION["id"],
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
    }
)

FAKE_CHARGE_REFUNDED = deepcopy(FAKE_CHARGE)
FAKE_CHARGE_REFUNDED = FAKE_CHARGE_REFUNDED.refund(
    amount=FAKE_CHARGE_REFUNDED["amount"]
)

FAKE_REFUND = {
    "id": "re_1E0he8KatMEEd8456454S01Vc",
    "object": "refund",
    "amount": FAKE_CHARGE_REFUNDED["amount_refunded"],
    "balance_transaction": "txn_1E0he8KaGRDEd998TDswMZuN",
    "charge": FAKE_CHARGE_REFUNDED["id"],
    "created": 1549425864,
    "currency": "usd",
    "metadata": {},
    "reason": None,
    "receipt_number": None,
    "source_transfer_reversal": None,
    "status": "succeeded",
    "transfer_reversal": None,
}

# Balance transaction associated with the refund
FAKE_BALANCE_TRANSACTION_REFUND = {
    "id": "txn_1E0he8KaGRDEd998TDswMZuN",
    "amount": -1 * FAKE_CHARGE_REFUNDED["amount_refunded"],
    "available_on": 1549425864,
    "created": 1549425864,
    "currency": "usd",
    "description": "REFUND FOR CHARGE (Payment for invoice G432DF1C-0028)",
    "exchange_rate": None,
    "fee": 0,
    "fee_details": [],
    "net": -1 * FAKE_CHARGE_REFUNDED["amount_refunded"],
    "object": "balance_transaction",
    "source": FAKE_REFUND["id"],
    "status": "available",
    "type": "refund",
}


FAKE_CHARGE_REFUNDED["refunds"].update(
    {"total_count": 1, "data": [deepcopy(FAKE_REFUND)]}
)


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


FAKE_PRODUCT = load_fixture("product_prod_fake1.json")

FAKE_PLAN = load_fixture("plan_gold21323.json")
FAKE_PLAN_II = load_fixture("plan_silver41294.json")

for plan in (FAKE_PLAN, FAKE_PLAN_II):
    # sanity check
    assert plan["product"] == FAKE_PRODUCT["id"]


FAKE_TIER_PLAN = {
    "id": "tier21323",
    "object": "plan",
    "active": True,
    "amount": None,
    "created": 1386247539,
    "currency": "usd",
    "interval": "month",
    "interval_count": 1,
    "livemode": False,
    "metadata": {},
    "nickname": "New plan name",
    "product": FAKE_PRODUCT["id"],
    "trial_period_days": None,
    "usage_type": "licensed",
    "tiers_mode": "graduated",
    "tiers": [
        {"flat_amount": 4900, "unit_amount": 1000, "up_to": 5},
        {"flat_amount": None, "unit_amount": 900, "up_to": None},
    ],
}

FAKE_PLAN_METERED = {
    "id": "plan_fakemetered",
    "object": "plan",
    "active": True,
    "aggregate_usage": "sum",
    "amount": 200,
    "collection_method": "per_unit",
    "created": 1552632817,
    "currency": "usd",
    "interval": "month",
    "interval_count": 1,
    "livemode": False,
    "metadata": {},
    "nickname": "Sum Metered Plan",
    "product": FAKE_PRODUCT["id"],
    "tiers": None,
    "tiers_mode": None,
    "transform_usage": None,
    "trial_period_days": None,
    "usage_type": "metered",
}


class SubscriptionDict(StripeItem):
    def __init__(self, *args, **kwargs):
        """Match Stripe's behavior: return a stripe iterable on `subscription.items`."""
        super().__init__(*args, **kwargs)
        self["items"] = StripeList(self["items"])

    def __setattr__(self, name, value):
        if type(value) == datetime:
            value = datetime_to_unix(value)

        # Special case for plan
        if name == "plan":
            for plan in [FAKE_PLAN, FAKE_PLAN_II, FAKE_TIER_PLAN, FAKE_PLAN_METERED]:
                if value == plan["id"]:
                    value = plan

        self[name] = value

    def delete(self, **kwargs):
        if "at_period_end" in kwargs:
            self["cancel_at_period_end"] = kwargs["at_period_end"]

        return self

    def save(self, idempotency_key=None):
        return self


FAKE_SUBSCRIPTION = SubscriptionDict(
    load_fixture("subscription_sub_fakefakefakefakefake0001.json")
)

FAKE_SUBSCRIPTION_NOT_PERIOD_CURRENT = deepcopy(FAKE_SUBSCRIPTION)
FAKE_SUBSCRIPTION_NOT_PERIOD_CURRENT.update(
    {"current_period_end": 1441907581, "current_period_start": 1439229181}
)

FAKE_SUBSCRIPTION_CANCELED = deepcopy(FAKE_SUBSCRIPTION)
FAKE_SUBSCRIPTION_CANCELED["status"] = "canceled"
FAKE_SUBSCRIPTION_CANCELED["canceled_at"] = 1440907580

FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END = deepcopy(FAKE_SUBSCRIPTION)
FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END["canceled_at"] = 1440907580
FAKE_SUBSCRIPTION_CANCELED_AT_PERIOD_END["cancel_at_period_end"] = True

FAKE_SUBSCRIPTION_II = SubscriptionDict(
    load_fixture("subscription_sub_fakefakefakefakefake0002.json")
)


FAKE_SUBSCRIPTION_III = SubscriptionDict(
    load_fixture("subscription_sub_fakefakefakefakefake0003.json")
)


FAKE_SUBSCRIPTION_MULTI_PLAN = SubscriptionDict(
    load_fixture("subscription_sub_fakefakefakefakefake0004.json")
)


FAKE_SUBSCRIPTION_METERED = SubscriptionDict(
    {
        "id": "sub_1rn1dp7WgjMtx9",
        "object": "subscription",
        "application_fee_percent": None,
        "collection_method": "charge_automatically",
        "cancel_at_period_end": False,
        "canceled_at": None,
        "current_period_end": 1441907581,
        "current_period_start": 1439229181,
        "customer": "cus_6lsBvm5rJ0zyHc",
        "discount": None,
        "ended_at": None,
        "metadata": {"djstripe_test_fake_id": "sub_fakefakefakefakefake0005"},
        "items": {
            "data": [
                {
                    "created": 1441907581,
                    "id": "si_UXYmKmJp6aWTw6",
                    "metadata": {},
                    "object": "subscription_item",
                    "plan": deepcopy(FAKE_PLAN_METERED),
                    "subscription": "sub_1rn1dp7WgjMtx9",
                }
            ]
        },
        "plan": deepcopy(FAKE_PLAN_METERED),
        "quantity": 1,
        "start": 1439229181,
        "start_date": 1439229181,
        "status": "active",
        "tax_percent": None,
        "trial_end": None,
        "trial_start": None,
    }
)


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


def convert_source_dict(data):
    if data:
        source_type = data["object"]
        if source_type == "card":
            data = CardDict(data)
        elif source_type == "bank_account":
            data = BankAccountDict(data)
        elif source_type == "source":
            data = SourceDict(data)
        else:
            raise ValueError("Unknown source type: {}".format(source_type))

    return data


class CustomerDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self["default_source"] = convert_source_dict(self["default_source"])

        for n, d in enumerate(self["sources"].get("data", [])):
            self["sources"]["data"][n] = convert_source_dict(d)

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


FAKE_CUSTOMER = CustomerDict(load_fixture("customer_cus_6lsBvm5rJ0zyHc.json"))


FAKE_CUSTOMER_II = CustomerDict(load_fixture("customer_cus_4UbFSo9tl62jqj.json"))


# Customer with a Source (instead of Card) as default_source
FAKE_CUSTOMER_III = CustomerDict(load_fixture("customer_cus_4QWKsZuuTHcs7X.json"))


# Customer with a Bank Account as default_source
FAKE_CUSTOMER_IV = CustomerDict(
    load_fixture("customer_cus_example_with_bank_account.json")
)


FAKE_DISCOUNT_CUSTOMER = {
    "object": "discount",
    "coupon": deepcopy(FAKE_COUPON),
    "customer": FAKE_CUSTOMER["id"],
    "start": 1493206114,
    "end": None,
    "subscription": None,
}


class InvoiceDict(StripeItem):
    def __init__(self, *args, **kwargs):
        """Match Stripe's behavior: return a stripe iterable on `invoice.lines`."""
        super().__init__(*args, **kwargs)
        self.lines = StripeList(self.lines)

    def pay(self):
        return self


FAKE_INVOICE = InvoiceDict(load_fixture("invoice_in_fakefakefakefakefake0001.json"))
FAKE_INVOICE_IV = InvoiceDict(load_fixture("invoice_in_fakefakefakefakefake0004.json"))


FAKE_INVOICE_II = InvoiceDict(
    {
        "id": "in_16af5A2eZvKYlo2CJjANLL81",
        "object": "invoice",
        "amount_due": 3000,
        "amount_paid": 0,
        "amount_remaining": 3000,
        "application_fee_amount": None,
        "attempt_count": 1,
        "attempted": True,
        "auto_advance": True,
        "collection_method": "charge_automatically",
        "charge": FAKE_CHARGE_II["id"],
        "currency": "usd",
        "customer": "cus_4UbFSo9tl62jqj",
        "created": 1439785128,
        "description": None,
        "discount": None,
        "due_date": None,
        "ending_balance": 0,
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
                    "period": {"start": 1442469907, "end": 1445061907},
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
    }
)


FAKE_INVOICE_III = InvoiceDict(
    {
        "id": "in_16Z9dP2eZvKYlo2CgFHgFx2Z",
        "object": "invoice",
        "amount_due": 0,
        "amount_paid": 0,
        "amount_remaining": 0,
        "application_fee_amount": None,
        "attempt_count": 0,
        "attempted": True,
        "auto_advance": True,
        "collection_method": "charge_automatically",
        "charge": None,
        "created": 1439425915,
        "currency": "usd",
        "customer": "cus_6lsBvm5rJ0zyHc",
        "description": None,
        "discount": None,
        "due_date": None,
        "ending_balance": 20,
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
                    "period": {"start": 1442111228, "end": 1444703228},
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
    }
)

FAKE_UPCOMING_INVOICE = InvoiceDict(
    {
        "id": "in",
        "object": "invoice",
        "amount_due": 2000,
        "amount_paid": 0,
        "amount_remaining": 2000,
        "application_fee_amount": None,
        "attempt_count": 1,
        "attempted": False,
        "collection_method": "charge_automatically",
        "charge": None,
        "created": 1439218864,
        "currency": "usd",
        "customer": FAKE_CUSTOMER["id"],
        "description": None,
        "default_tax_rates": [
            {
                "id": "txr_fakefakefakefakefake0001",
                "object": "tax_rate",
                "active": True,
                "created": 1570921289,
                "description": None,
                "display_name": "VAT",
                "inclusive": True,
                "jurisdiction": "Example1",
                "livemode": False,
                "metadata": {"djstripe_test_fake_id": "txr_fakefakefakefakefake0001"},
                "percentage": 15.0,
            }
        ],
        "discount": None,
        "due_date": None,
        "ending_balance": None,
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
                    "period": {"start": 1441907581, "end": 1444499581},
                    "plan": deepcopy(FAKE_PLAN),
                    "proration": False,
                    "quantity": 1,
                    "subscription": None,
                    "tax_amounts": [
                        {
                            "amount": 261,
                            "inclusive": True,
                            "tax_rate": "txr_fakefakefakefakefake0001",
                        }
                    ],
                    "tax_rates": [],
                    "type": "subscription",
                }
            ],
            "total_count": 1,
            "object": "list",
            "url": "/v1/invoices/in_fakefakefakefakefake0001/lines",
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
        "tax": 261,
        "tax_percent": None,
        "total": 2000,
        "total_tax_amounts": [
            {
                "amount": 261,
                "inclusive": True,
                "tax_rate": "txr_fakefakefakefakefake0001",
            }
        ],
        "webhooks_delivered_at": 1439218870,
    }
)

FAKE_TAX_RATE_EXAMPLE_1_VAT = load_fixture("tax_rate_txr_fakefakefakefakefake0001.json")
FAKE_TAX_RATE_EXAMPLE_2_SALES = load_fixture(
    "tax_rate_txr_fakefakefakefakefake0002.json"
)

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
    "metadata": {"key1": "value1", "key2": "value2"},
    "period": {"start": 1439033216, "end": 1439033216},
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
    "metadata": {"key1": "value1", "key2": "value2"},
    "period": {"start": 1439033216, "end": 1439033216},
    "plan": None,
    "proration": False,
    "quantity": None,
    "subscription": None,
}

# Invoice item with tax_rates
# TODO generate this
FAKE_INVOICEITEM_III = {
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
    "metadata": {"key1": "value1", "key2": "value2"},
    "period": {"start": 1439033216, "end": 1439033216},
    "plan": None,
    "proration": False,
    "quantity": None,
    "subscription": None,
    "tax_rates": [FAKE_TAX_RATE_EXAMPLE_1_VAT],
}


FAKE_TRANSFER = {
    "id": "tr_16Y9BK2eZvKYlo2CR0ySu1BA",
    "object": "transfer",
    "amount": 100,
    "amount_reversed": 0,
    "application_fee_amount": None,
    "balance_transaction": deepcopy(FAKE_BALANCE_TRANSACTION_II),
    "created": 1439185846,
    "currency": "usd",
    "description": "Test description - 1439185984",
    "destination": "acct_16Y9B9Fso9hLaeLu",
    "destination_payment": "py_16Y9BKFso9hLaeLueFmWAYUi",
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
}

FAKE_TRANSFER_II = {
    "id": "tr_16hTzv2eZvKYlo2CWuyMmuvV",
    "object": "transfer",
    "amount": 2000,
    "amount_reversed": 0,
    "application_fee_amount": None,
    "balance_transaction": deepcopy(FAKE_BALANCE_TRANSACTION_III),
    "bank_account": deepcopy(FAKE_BANK_ACCOUNT),
    "created": 1440420000,
    "currency": "usd",
    "description": None,
    "destination": "ba_16hTzo2eZvKYlo2CeSjfb0tS",
    "livemode": False,
    "metadata": {"foo": "bar"},
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
}

FAKE_TRANSFER_III = {
    "id": "tr_17O4U52eZvKYlo2CmyYbDAEy",
    "object": "transfer",
    "amount": 19010,
    "amount_reversed": 0,
    "application_fee_amount": None,
    "balance_transaction": deepcopy(FAKE_BALANCE_TRANSACTION_IV),
    "bank_account": deepcopy(FAKE_BANK_ACCOUNT_II),
    "created": 1451560845,
    "currency": "usd",
    "date": 1451560845,
    "description": "Transfer+for+test@example.com",
    "destination": "ba_17O4Tz2eZvKYlo2CMYsxroV5",
    "livemode": False,
    "metadata": {"foo2": "bar2"},
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
}

FAKE_ACCOUNT = {
    "id": "acct_1032D82eZvKYlo2C",
    "object": "account",
    "business_profile": {
        "name": "dj-stripe",
        "support_email": "djstripe@example.com",
        "support_phone": None,
        "support_url": "https://example.com/support/",
        # TODO - change this since stripe validation actually doesn't allow example.com
        "url": "https://example.com",
    },
    "settings": {
        "branding": {
            "icon": "file_4hshrsKatMEEd6736724HYAXyj",
            "logo": "file_1E3fssKatMEEd6736724HYAXyj",
            "primary_color": "#092e20",
        },
        "dashboard": {"display_name": "dj-stripe", "timezone": "Etc/UTC"},
        "payments": {"statement_descriptor": "DJSTRIPE"},
    },
    "charges_enabled": True,
    "country": "US",
    "default_currency": "usd",
    "details_submitted": True,
    "email": "djstripe@example.com",
    "payouts_enabled": True,
    "type": "standard",
}

FAKE_FILEUPLOAD_LOGO = {
    "created": 1550134074,
    "filename": "logo_preview.png",
    "id": "file_1E3fssKatMEEd6736724HYAXyj",
    "links": {
        "data": [
            {
                "created": 1550134074,
                "expired": False,
                "expires_at": None,
                "file": "file_1E3fssKatMEEd6736724HYAXyj",
                "id": "link_1E3fssKatMEEd673672V0JSH",
                "livemode": False,
                "metadata": {},
                "object": "file_link",
                "url": (
                    "https://files.stripe.com/links/fl_test_69vG4ISDx9Chjklasrf06BJeQo"
                ),
            }
        ],
        "has_more": False,
        "object": "list",
        "url": "/v1/file_links?file=file_1E3fssKatMEEd6736724HYAXyj",
    },
    "object": "file_upload",
    "purpose": "business_logo",
    "size": 6650,
    "type": "png",
    "url": "https://files.stripe.com/files/f_test_BTJFKcS7VDahgkjqw8EVNWlM",
}


FAKE_FILEUPLOAD_ICON = {
    "created": 1550134074,
    "filename": "icon_preview.png",
    "id": "file_4hshrsKatMEEd6736724HYAXyj",
    "links": {
        "data": [
            {
                "created": 1550134074,
                "expired": False,
                "expires_at": None,
                "file": "file_4hshrsKatMEEd6736724HYAXyj",
                "id": "link_4jsdgsKatMEEd673672V0JSH",
                "livemode": False,
                "metadata": {},
                "object": "file_link",
                "url": (
                    "https://files.stripe.com/links/fl_test_69vG4ISDx9Chjklasrf06BJeQo"
                ),
            }
        ],
        "has_more": False,
        "object": "list",
        "url": "/v1/file_links?file=file_4hshrsKatMEEd6736724HYAXyj",
    },
    "object": "file_upload",
    # Note that purpose="business_logo" for both icon and logo fields
    "purpose": "business_logo",
    "size": 6650,
    "type": "png",
    "url": "https://files.stripe.com/files/f_test_BTJFKcS7VDahgkjqw8EVNWlM",
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
    "data": {"object": FAKE_PLAN, "previous_attributes": {"name": "Plan anual test4"}},
    "livemode": False,
    "pending_webhooks": 1,
    "request": {"id": "req_AyamqQWoi5AMR2", "idempotency_key": None},
    "type": "plan.updated",
}

FAKE_EVENT_CHARGE_SUCCEEDED = {
    "id": "evt_16YKQi2eZvKYlo2CT2oe5ff3",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_CHARGE)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6lsB7hkicwhaDj",
    "type": "charge.succeeded",
}

FAKE_EVENT_TEST_CHARGE_SUCCEEDED = deepcopy(FAKE_EVENT_CHARGE_SUCCEEDED)
FAKE_EVENT_TEST_CHARGE_SUCCEEDED["id"] = TEST_EVENT_ID

FAKE_EVENT_CUSTOMER_CREATED = {
    "id": "evt_38DHch3whaDvKYlo2CT2oe5ff3",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_CUSTOMER)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6l38DHch3whaDj",
    "type": "customer.created",
}

FAKE_EVENT_CUSTOMER_DELETED = deepcopy(FAKE_EVENT_CUSTOMER_CREATED)
FAKE_EVENT_CUSTOMER_DELETED.update(
    {"id": "evt_38DHch3whaDvKYlo2jksfsFFxy", "type": "customer.deleted"}
)

FAKE_EVENT_CUSTOMER_DISCOUNT_CREATED = {
    "id": "evt_test_customer.discount.created",
    "object": "event",
    "api_version": "2018-05-21",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_DISCOUNT_CUSTOMER)},
    "livemode": False,
    "pending_webhooks": 1,
    "request": {"id": "req_6l38DHch3whaDj", "idempotency_key": None},
    "type": "customer.discount.created",
}


FAKE_EVENT_CUSTOMER_DISCOUNT_DELETED = {
    "id": "AGBWvF5zBm4sMCsLLPZrw9XX",
    "type": "customer.discount.deleted",
    "api_version": "2017-02-14",
    "created": 1439229084,
    "object": "event",
    "pending_webhooks": 0,
    "request": "req_6l38DHch3whaDj",
    "data": {"object": deepcopy(FAKE_DISCOUNT_CUSTOMER)},
}

FAKE_EVENT_CUSTOMER_SOURCE_CREATED = {
    "id": "evt_DvKYlo38huDvKYlo2C7SXedrZk",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_CARD)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_o3whaDvh3whaDj",
    "type": "customer.source.created",
}

FAKE_EVENT_CUSTOMER_SOURCE_DELETED = deepcopy(FAKE_EVENT_CUSTOMER_SOURCE_CREATED)
FAKE_EVENT_CUSTOMER_SOURCE_DELETED.update(
    {"id": "evt_DvKYlo38huDvKYlo2C7SXedrYk", "type": "customer.source.deleted"}
)

FAKE_EVENT_CUSTOMER_SOURCE_DELETED_DUPE = deepcopy(FAKE_EVENT_CUSTOMER_SOURCE_DELETED)
FAKE_EVENT_CUSTOMER_SOURCE_DELETED_DUPE.update({"id": "evt_DvKYlo38huDvKYlo2C7SXedzAk"})

FAKE_EVENT_CUSTOMER_SUBSCRIPTION_CREATED = {
    "id": "evt_38DHch3wHD2eZvKYlCT2oe5ff3",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_SUBSCRIPTION)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6l87IHch3diaDj",
    "type": "customer.subscription.created",
}

FAKE_EVENT_CUSTOMER_SUBSCRIPTION_DELETED = deepcopy(
    FAKE_EVENT_CUSTOMER_SUBSCRIPTION_CREATED
)
FAKE_EVENT_CUSTOMER_SUBSCRIPTION_DELETED.update(
    {"id": "evt_38DHch3wHD2eZvKYlCT2oeryaf", "type": "customer.subscription.deleted"}
)

FAKE_EVENT_DISPUTE_CREATED = {
    "id": "evt_16YKQi2eZvKYlo2CT2oe5ff3",
    "object": "event",
    "api_version": "2017-08-15",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_DISPUTE)},
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
    "data": {"object": deepcopy(FAKE_INVOICE)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_8O4sB7hkDobVT",
    "type": "invoice.created",
}

FAKE_EVENT_INVOICE_DELETED = deepcopy(FAKE_EVENT_INVOICE_CREATED)
FAKE_EVENT_INVOICE_DELETED.update(
    {"id": "evt_187IHD2eZvKYlo2Cjkjsr34H", "type": "invoice.deleted"}
)

FAKE_EVENT_INVOICE_UPCOMING = {
    "id": "evt_187IHD2eZvKYlo2C6YKQi2bc",
    "object": "event",
    "api_version": "2017-02-14",
    "created": 1501859641,
    "data": {"object": deepcopy(FAKE_INVOICE)},
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
    "data": {"object": deepcopy(FAKE_INVOICEITEM)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_8O4Qbs2EDobDVT",
    "type": "invoiceitem.created",
}

FAKE_EVENT_INVOICEITEM_DELETED = deepcopy(FAKE_EVENT_INVOICEITEM_CREATED)
FAKE_EVENT_INVOICEITEM_DELETED.update(
    {"id": "evt_187IHD2eZvKYloJfdsnnfs34", "type": "invoiceitem.deleted"}
)

FAKE_EVENT_PAYMENT_METHOD_ATTACHED = {
    "id": "evt_1FDOwDKatMEEd998o5FyxxAB",
    "object": "event",
    "api_version": "2019-08-14",
    "created": 1567228549,
    "data": {"object": deepcopy(FAKE_PAYMENT_METHOD_I)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": {"id": "req_9c9djVqxUZIKNr", "idempotency_key": None},
    "type": "payment_method.attached",
}

FAKE_EVENT_PAYMENT_METHOD_DETACHED = {
    "id": "evt_1FDOwDKatMEEd998o5Fdadfds",
    "object": "event",
    "api_version": "2019-08-14",
    "created": 1567228549,
    "data": {"object": deepcopy(FAKE_PAYMENT_METHOD_I)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": {"id": "req_9c9djVqxcxgdfg", "idempotency_key": None},
    "type": "payment_method.detached",
}
FAKE_EVENT_PAYMENT_METHOD_DETACHED["data"]["object"]["customer"] = None

FAKE_EVENT_CARD_PAYMENT_METHOD_ATTACHED = {
    "id": "evt_1FDOwDKatMEEd998o5Fghgfh",
    "object": "event",
    "api_version": "2019-08-14",
    "created": 1567228549,
    "data": {"object": deepcopy(FAKE_CARD_AS_PAYMENT_METHOD)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": {"id": "req_9c9djVqxUhgfh", "idempotency_key": None},
    "type": "payment_method.attached",
}

FAKE_EVENT_CARD_PAYMENT_METHOD_DETACHED = {
    "id": "evt_1FDOwDKatMEEd998o5435345",
    "object": "event",
    "api_version": "2019-08-14",
    "created": 1567228549,
    "data": {"object": deepcopy(FAKE_CARD_AS_PAYMENT_METHOD)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": {"id": "req_9c9djVqx6tgeg", "idempotency_key": None},
    "type": "payment_method.detached",
}
# Note that the event from Stripe doesn't have customer = None


FAKE_EVENT_PLAN_CREATED = {
    "id": "evt_1877X72eZvKYlo2CLK6daFxu",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1462297325,
    "data": {"object": deepcopy(FAKE_PLAN)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_8NtJXPttxSvFyM",
    "type": "plan.created",
}

FAKE_EVENT_PLAN_DELETED = deepcopy(FAKE_EVENT_PLAN_CREATED)
FAKE_EVENT_PLAN_DELETED.update(
    {"id": "evt_1877X72eZvKYl2jkds32jJFc", "type": "plan.deleted"}
)

FAKE_EVENT_TRANSFER_CREATED = {
    "id": "evt_16igNU2eZvKYlo2CYyMkYvet",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1441696732,
    "data": {"object": deepcopy(FAKE_TRANSFER)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6wZW9MskhYU15Y",
    "type": "transfer.created",
}

FAKE_EVENT_TRANSFER_DELETED = deepcopy(FAKE_EVENT_TRANSFER_CREATED)
FAKE_EVENT_TRANSFER_DELETED.update(
    {"id": "evt_16igNU2eZvKjklfsdjk232Mf", "type": "transfer.deleted"}
)

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

FAKE_PAYMENT_INTENT_DESTINATION_CHARGE = {
    "id": "pi_1FG742B7kbjcJ8QqGKF6qIM0",
    "object": "payment_intent",
    "amount": 190200,
    "amount_capturable": 0,
    "amount_received": 190200,
    "application": None,
    "application_fee_amount": None,
    "canceled_at": None,
    "cancellation_reason": None,
    "capture_method": "automatic",
    "charges": {
        "object": "list",
        "data": [
            {
                "id": "ch_fakefakefakefakefake0001",
                "object": "charge",
                "amount": 190200,
                "amount_refunded": 0,
                "application": None,
                "application_fee": None,
                "application_fee_amount": None,
                "balance_transaction": "txn_fake_ch_fakefakefakefakefake0001",
                "billing_details": {
                    "address": {
                        "city": None,
                        "country": "US",
                        "line1": None,
                        "line2": None,
                        "postal_code": "92082",
                        "state": None,
                    },
                    "email": "kyoung@hotmail.com",
                    "name": "John Foo",
                    "phone": None,
                },
                "captured": True,
                "created": 1567874856,
                "currency": "usd",
                "customer": "cus_6lsBvm5rJ0zyHc",
                "description": "Online payment for FOO",
                "destination": "acct_1032D82eZvKYlo2C",
                "dispute": None,
                "failure_code": None,
                "failure_message": None,
                "fraud_details": {},
                "invoice": None,
                "livemode": False,
                "metadata": {"foo": "bar"},
                "on_behalf_of": "acct_1032D82eZvKYlo2C",
                "order": None,
                "outcome": {
                    "network_status": "approved_by_network",
                    "reason": None,
                    "risk_level": "normal",
                    "risk_score": 47,
                    "seller_message": "Payment complete.",
                    "type": "authorized",
                },
                "paid": True,
                "payment_intent": "pi_1FG742B7kbjcJ8QqGKF6qIM0",
                "payment_method": "pm_1FG74VB7kbjcJ8QqXqULdSAV",
                "payment_method_details": {
                    "card": {
                        "brand": "visa",
                        "checks": {
                            "address_line1_check": None,
                            "address_postal_code_check": "pass",
                            "cvc_check": "pass",
                        },
                        "country": "US",
                        "exp_month": 10,
                        "exp_year": 2020,
                        "fingerprint": "sb2OAOijRKy8wYHu",
                        "funding": "credit",
                        "last4": "4242",
                        "three_d_secure": None,
                        "wallet": None,
                    },
                    "type": "card",
                },
                "receipt_email": "kyoung@hotmail.com",
                "receipt_number": None,
                "receipt_url": (
                    "https://pay.stripe.com/receipts/acct_1DrGYIB7kbjcJ8Qq/"
                    "ch_1FG74WB7kbjcJ8Qqx1oIdqfG/rcpt_FleN33oToRTXKCy6sxd5Stnh0ttnxYT"
                ),
                "refunded": False,
                "refunds": {
                    "object": "list",
                    "data": [],
                    "has_more": False,
                    "total_count": 0,
                    "url": "/v1/charges/ch_1FG74WB7kbjcJ8Qqx1oIdqfG/refunds",
                },
                "review": None,
                "shipping": None,
                "source": None,
                "source_transfer": None,
                "statement_descriptor": "FOO DESCRIPTOR",
                "statement_descriptor_suffix": None,
                "status": "succeeded",
                "transfer": "tr_16Y9BK2eZvKYlo2CR0ySu1BA",
                "transfer_data": {
                    "amount": None,
                    "destination": "acct_1032D82eZvKYlo2C",
                },
                "transfer_group": "group_pi_1FG742B7kbjcJ8QqGKF6qIM0",
            }
        ],
        "has_more": False,
        "total_count": 1,
        "url": "/v1/charges?payment_intent=pi_1FG742B7kbjcJ8QqGKF6qIM0",
    },
    "client_secret": "pi_1FG742B7kbjcJ8QqGKF6qIM0_secret_yeRoAechksXUy2HdUydIKlGbw",
    "confirmation_method": "automatic",
    "created": 1567874826,
    "currency": "usd",
    "customer": "cus_6lsBvm5rJ0zyHc",
    "description": "Online payment for FOO",
    "invoice": None,
    "last_payment_error": None,
    "livemode": False,
    "metadata": {"foo": "bar"},
    "next_action": None,
    "on_behalf_of": "acct_1032D82eZvKYlo2C",
    "payment_method": "pm_fakefakefakefake0001",
    "payment_method_options": {"card": {"request_three_d_secure": "automatic"}},
    "payment_method_types": ["card"],
    "receipt_email": "kyoung@hotmail.com",
    "review": None,
    "setup_future_usage": None,
    "shipping": None,
    "source": None,
    "statement_descriptor": "FOO DESCRIPTOR",
    "statement_descriptor_suffix": None,
    "status": "succeeded",
    "transfer_data": {"destination": "acct_1032D82eZvKYlo2C"},
    "transfer_group": "group_pi_1FG742B7kbjcJ8QqGKF6qIM0",
}

FAKE_EVENT_PAYMENT_INTENT_SUCCEEDED_DESTINATION_CHARGE = {
    "id": "evt_1FG74XB7kbjcJ8Qq22i2BPdt",
    "object": "event",
    "api_version": "2019-05-16",
    "created": 1567874857,
    "data": {"object": deepcopy(FAKE_PAYMENT_INTENT_DESTINATION_CHARGE)},
    "livemode": False,
    "pending_webhooks": 1,
    "request": {"id": "req_AJAmnJE4eiPIzb", "idempotency_key": None},
    "type": "payment_intent.succeeded",
}
