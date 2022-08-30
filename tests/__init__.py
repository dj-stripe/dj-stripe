"""
A Fake or multiple fakes for each stripe object.

Originally collected using API VERSION 2015-07-28.
Updated to API VERSION 2016-03-07 with bogus fields.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import logging
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import dateformat, timezone

from djstripe.webhooks import TEST_EVENT_ID

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
logger = logging.getLogger(__name__)

FUTURE_DATE = datetime(2100, 4, 30, tzinfo=timezone.utc)

FIXTURE_DIR_PATH = Path(__file__).parent.joinpath("fixtures")


class AssertStripeFksMixin:
    def _get_field_str(self, field) -> str:
        if isinstance(field, models.OneToOneRel):
            if field.parent_link:
                return ""
            else:
                reverse_id_name = str(field.remote_field.foreign_related_fields[0])
                return (
                    reverse_id_name.replace("djstripe_id", field.name)
                    + " (related name)"
                )

        elif isinstance(field, models.ForeignKey):
            return str(field)

        else:
            return ""

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
            field_str = self._get_field_str(field)
            if not field_str or field_str.endswith(".djstripe_owner_account"):
                continue

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

    @classmethod
    def class_url(cls):
        return "/v1/test-items/"

    def instance_url(self):
        """Superficial mock that emulates instance_url."""
        id = self.get("id")
        base = self.class_url()
        return "%s/%s" % (base, id)

    def request(self, method, url, params) -> Dict:
        """Superficial mock that emulates request method."""
        assert method == "post"
        for key, value in params.items():
            self.__setattr__(key, value)
        return self


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


class ExternalAccounts(object):
    def __init__(self, external_account_fakes):
        self.external_account_fakes = external_account_fakes

    def create(self, source, api_key=None):
        for fake_external_account in self.external_account_fakes:
            if fake_external_account["id"] == source:
                return fake_external_account

    def retrieve(self, id, expand=None):
        for fake_external_account in self.external_account_fakes:
            if fake_external_account["id"] == id:
                return fake_external_account

    def list(self, **kwargs):
        return StripeList(data=self.external_account_fakes)


class AccountDict(dict):
    def save(self, idempotency_key=None):
        return self

    @property
    def external_accounts(self):
        return ExternalAccounts(
            external_account_fakes=self["external_accounts"]["data"]
        )

    def create(self):
        from djstripe.models import Account

        return Account.sync_from_stripe_data(self)


FAKE_STANDARD_ACCOUNT = AccountDict(
    load_fixture("account_standard_acct_1Fg9jUA3kq9o1aTc.json")
)

# Stripe Platform Account to which the STRIPE_SECRET_KEY belongs to
FAKE_PLATFORM_ACCOUNT = deepcopy(FAKE_STANDARD_ACCOUNT)
FAKE_PLATFORM_ACCOUNT["settings"]["dashboard"]["display_name"] = "djstripe-platform"

FAKE_CUSTOM_ACCOUNT = AccountDict(
    load_fixture("account_custom_acct_1IuHosQveW0ONQsd.json")
)

FAKE_EXPRESS_ACCOUNT = AccountDict(
    load_fixture("account_express_acct_1IuHosQveW0ONQsd.json")
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

# Stripe Customer Bank Account Payment Source
FAKE_BANK_ACCOUNT_SOURCE = BankAccountDict(
    load_fixture("bank_account_ba_fakefakefakefakefake0003.json")
)
FAKE_BANK_ACCOUNT_IV = BankAccountDict(
    load_fixture("bank_account_ba_fakefakefakefakefake0004.json")
)


class CardDict(LegacySourceDict):
    pass


FAKE_CARD = CardDict(load_fixture("card_card_fakefakefakefakefake0001.json"))

FAKE_CARD_II = CardDict(load_fixture("card_card_fakefakefakefakefake0002.json"))

FAKE_CARD_III = CardDict(load_fixture("card_card_fakefakefakefakefake0003.json"))

# Stripe Custom Connected Account Card Payout Source
FAKE_CARD_IV = CardDict(load_fixture("card_card_fakefakefakefakefake0004.json"))


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

FAKE_PAYMENT_INTENT_II = deepcopy(FAKE_PAYMENT_INTENT_I)
FAKE_PAYMENT_INTENT_II["customer"] = "cus_4UbFSo9tl62jqj"  # FAKE_CUSTOMER_II

FAKE_PAYMENT_INTENT_DESTINATION_CHARGE = load_fixture(
    "payment_intent_pi_destination_charge.json"
)


class PaymentMethodDict(dict):
    def detach(self):
        self.pop("customer")
        return self


FAKE_PAYMENT_METHOD_I = PaymentMethodDict(
    load_fixture("payment_method_pm_fakefakefakefake0001.json")
)

FAKE_PAYMENT_METHOD_II = deepcopy(FAKE_PAYMENT_METHOD_I)
FAKE_PAYMENT_METHOD_II["customer"] = "cus_4UbFSo9tl62jqj"  # FAKE_CUSTOMER_II

# FAKE_CARD, but accessed as a PaymentMethod
FAKE_CARD_AS_PAYMENT_METHOD = PaymentMethodDict(
    load_fixture("payment_method_card_fakefakefakefakefake0001.json")
)


FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT = load_fixture(
    "order_order_fakefakefakefake0001.json"
)


FAKE_ORDER_WITHOUT_CUSTOMER_WITH_PAYMENT_INTENT = deepcopy(
    FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT
)
FAKE_ORDER_WITHOUT_CUSTOMER_WITH_PAYMENT_INTENT["customer"] = None


FAKE_ORDER_WITH_CUSTOMER_WITHOUT_PAYMENT_INTENT = deepcopy(
    FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT
)
FAKE_ORDER_WITH_CUSTOMER_WITHOUT_PAYMENT_INTENT["payment_intent"] = None
FAKE_ORDER_WITH_CUSTOMER_WITHOUT_PAYMENT_INTENT["payment"]["payment_intent"] = None


FAKE_ORDER_WITHOUT_CUSTOMER_WITHOUT_PAYMENT_INTENT = deepcopy(
    FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT
)
FAKE_ORDER_WITHOUT_CUSTOMER_WITHOUT_PAYMENT_INTENT["customer"] = None
FAKE_ORDER_WITHOUT_CUSTOMER_WITHOUT_PAYMENT_INTENT["payment_intent"] = None
FAKE_ORDER_WITHOUT_CUSTOMER_WITHOUT_PAYMENT_INTENT["payment"]["payment_intent"] = None


# Created Orders have their status="open"
FAKE_EVENT_ORDER_CREATED = {
    "id": "evt_16igNU2eZvKYlo2CYyMkYvet",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1441696732,
    "data": {"object": deepcopy(FAKE_ORDER_WITH_CUSTOMER_WITHOUT_PAYMENT_INTENT)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6wZW9MskhYU15Y",
    "type": "order.created",
}
FAKE_EVENT_ORDER_CREATED["data"]["object"]["status"] = "open"


FAKE_EVENT_ORDER_UPDATED = {
    "id": "evt_16igNU2eZvKYlo2CYyMkYvet",
    "object": "event",
    "api_version": "2016-03-07",
    "created": 1441696732,
    "data": {"object": deepcopy(FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6wZW9MskhYU15Y",
    "type": "order.created",
}

FAKE_EVENT_ORDER_UPDATED["data"]["object"]["status"] = "open"
FAKE_EVENT_ORDER_UPDATED["type"] = "order.updated"
FAKE_EVENT_ORDER_UPDATED["data"]["object"]["billing_details"][
    "email"
] = "arnav13@gmail.com"


FAKE_EVENT_ORDER_SUBMITTED = deepcopy(FAKE_EVENT_ORDER_UPDATED)
FAKE_EVENT_ORDER_SUBMITTED["type"] = "order.submitted"
FAKE_EVENT_ORDER_SUBMITTED["data"]["object"]["status"] = "submitted"


FAKE_EVENT_ORDER_PROCESSING = deepcopy(FAKE_EVENT_ORDER_UPDATED)
FAKE_EVENT_ORDER_PROCESSING["type"] = "order.processing"
FAKE_EVENT_ORDER_PROCESSING["data"]["object"]["status"] = "processing"


FAKE_EVENT_ORDER_CANCELLED = deepcopy(FAKE_EVENT_ORDER_UPDATED)
FAKE_EVENT_ORDER_CANCELLED["type"] = "order.canceled"
FAKE_EVENT_ORDER_CANCELLED["data"]["object"]["status"] = "canceled"


FAKE_EVENT_ORDER_COMPLETED = deepcopy(FAKE_EVENT_ORDER_UPDATED)
FAKE_EVENT_ORDER_COMPLETED["type"] = "order.complete"
FAKE_EVENT_ORDER_COMPLETED["data"]["object"]["status"] = "complete"

# TODO - add to regenerate_test_fixtures and replace this with a JSON fixture
FAKE_SETUP_INTENT_I = {
    "id": "seti_fakefakefakefake0001",
    "object": "setup_intent",
    "cancellation_reason": None,
    "payment_method_types": ["card"],
    "status": "requires_payment_method",
    "usage": "off_session",
    "payment_method": None,
    "on_behalf_of": None,
    "customer": None,
}

FAKE_SETUP_INTENT_II = {
    "application": None,
    "cancellation_reason": None,
    "client_secret": "seti_1J0g0WJSZQVUcJYgWE2XSi1K_secret_Jdxw2mOaIEHBdE6eTsfJ2IfmamgNJaF",
    "created": 1623301244,
    "customer": "cus_6lsBvm5rJ0zyHc",
    "description": None,
    "id": "seti_1J0g0WJSZQVUcJYgWE2XSi1K",
    "last_setup_error": None,
    "latest_attempt": "setatt_1J0g0WJSZQVUcJYgsrFgwxVh",
    "livemode": False,
    "mandate": None,
    "metadata": {},
    "next_action": None,
    "object": "setup_intent",
    "on_behalf_of": None,
    "payment_method": "pm_fakefakefakefake0001",
    "payment_method_options": {"card": {"request_three_d_secure": "automatic"}},
    "payment_method_types": ["card"],
    "single_use_mandate": None,
    "status": "succeeded",
    "usage": "off_session",
}

FAKE_SETUP_INTENT_DESTINATION_CHARGE = load_fixture(
    "setup_intent_pi_destination_charge.json"
)


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
    "metadata": {},
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
        "amount_captured": 0,
        "amount_refunded": 0,
        "application_fee": None,
        "application_fee_amount": None,
        "balance_transaction": FAKE_BALANCE_TRANSACTION["id"],
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
        "calculated_statement_descriptor": "Stripe",
        "captured": False,
        "created": 1439788903,
        "currency": "usd",
        "customer": "cus_4UbFSo9tl62jqj",
        "description": None,
        "destination": None,
        "dispute": None,
        "disputed": False,
        "failure_code": "expired_card",
        "failure_message": "Your card has expired.",
        "fraud_details": {},
        "invoice": "in_16af5A2eZvKYlo2CJjANLL81",
        "livemode": False,
        "metadata": {},
        "on_behalf_of": None,
        "order": None,
        "outcome": {
            "network_status": "declined_by_network",
            "reason": "expired_card",
            "risk_level": "normal",
            "risk_score": 1,
            "seller_message": "The bank returned the decline code `expired_card`.",
            "type": "issuer_declined",
        },
        "paid": False,
        "payment_intent": FAKE_PAYMENT_INTENT_II["id"],
        "payment_method": FAKE_CARD_AS_PAYMENT_METHOD["id"],
        "payment_method_details": {
            "card": {
                "brand": "visa",
                "checks": {
                    "address_line1_check": None,
                    "address_postal_code_check": None,
                    "cvc_check": None,
                },
                "country": "US",
                "exp_month": 6,
                "exp_year": 2021,
                "fingerprint": "88PuXw9tEmvYe69o",
                "funding": "credit",
                "installments": None,
                "last4": "4242",
                "network": "visa",
                "three_d_secure": None,
                "wallet": None,
            },
            "type": "card",
        },
        "receipt_email": None,
        "receipt_number": None,
        "receipt_url": None,
        "refunded": False,
        "refunds": {
            "object": "list",
            "total_count": 0,
            "has_more": False,
            "url": "/v1/charges/ch_16ag432eZvKYlo2CGDe6lvVs/refunds",
            "data": [],
        },
        "review": None,
        "shipping": None,
        "source": deepcopy(FAKE_CARD_II),
        "source_transfer": None,
        "statement_descriptor": None,
        "statement_descriptor_suffix": None,
        "status": "failed",
        "transfer_data": None,
        "transfer_group": None,
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
    "applies_to": {"products": ["prod_fake1"]},
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


FAKE_DISPUTE_CHARGE = load_fixture("dispute_ch_fakefakefakefake01.json")

FAKE_DISPUTE_BALANCE_TRANSACTION = load_fixture("dispute_txn_fakefakefakefake01.json")

# case when a dispute gets closed and the funds get reinstated (full)
FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_FULL = deepcopy(
    FAKE_DISPUTE_BALANCE_TRANSACTION
)
FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_FULL["amount"] = (
    -1 * FAKE_DISPUTE_BALANCE_TRANSACTION["amount"]
)
FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_FULL["fee"] = (
    -1 * FAKE_DISPUTE_BALANCE_TRANSACTION["fee"]
)
FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_FULL["net"] = (
    -1 * FAKE_DISPUTE_BALANCE_TRANSACTION["net"]
)
FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_FULL["fee_details"][0]["amount"] = (
    -1 * FAKE_DISPUTE_BALANCE_TRANSACTION["fee_details"][0]["amount"]
)

# case when a dispute gets closed and the funds get reinstated (partial)
FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_PARTIAL = deepcopy(
    FAKE_DISPUTE_BALANCE_TRANSACTION
)
FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_PARTIAL["amount"] = (
    -0.9 * FAKE_DISPUTE_BALANCE_TRANSACTION["amount"]
)
FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_PARTIAL["fee"] = (
    -0.9 * FAKE_DISPUTE_BALANCE_TRANSACTION["fee"]
)
FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_PARTIAL["net"] = (
    -0.9 * FAKE_DISPUTE_BALANCE_TRANSACTION["net"]
)
FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_PARTIAL["fee_details"][0]["amount"] = (
    -0.9 * FAKE_DISPUTE_BALANCE_TRANSACTION["fee_details"][0]["amount"]
)


FAKE_DISPUTE_PAYMENT_INTENT = load_fixture("dispute_pi_fakefakefakefake01.json")

FAKE_DISPUTE_PAYMENT_METHOD = load_fixture("dispute_pm_fakefakefakefake01.json")

# case when dispute gets created
FAKE_DISPUTE_I = load_fixture("dispute_dp_fakefakefakefake01.json")

# case when funds get withdrawn from platform account due to dispute
FAKE_DISPUTE_II = load_fixture("dispute_dp_fakefakefakefake02.json")

# case when dispute gets updated
FAKE_DISPUTE_III = deepcopy(FAKE_DISPUTE_II)
FAKE_DISPUTE_III["evidence"]["receipt"] = "file_4hshrsKatMEEd6736724HYAXyj"

# case when dispute gets closed
FAKE_DISPUTE_IV = deepcopy(FAKE_DISPUTE_II)
FAKE_DISPUTE_IV["evidence"]["receipt"] = "file_4hshrsKatMEEd6736724HYAXyj"
FAKE_DISPUTE_IV["status"] = "won"

# case when dispute funds get reinstated (partial)
FAKE_DISPUTE_V_PARTIAL = load_fixture("dispute_dp_funds_reinstated_full.json")
FAKE_DISPUTE_V_PARTIAL["balance_transactions"][
    1
] = FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_PARTIAL


# case when dispute funds get reinstated (full)
FAKE_DISPUTE_V_FULL = load_fixture("dispute_dp_funds_reinstated_full.json")
FAKE_DISPUTE_V_FULL["balance_transactions"][
    1
] = FAKE_DISPUTE_BALANCE_TRANSACTION_REFUND_FULL


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
    "billing_scheme": "per_unit",
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


FAKE_PRICE = load_fixture("price_gold21323.json")
FAKE_PRICE_II = load_fixture("price_silver41294.json")

for price in (FAKE_PRICE, FAKE_PRICE_II):
    # sanity check
    assert price["product"] == FAKE_PRODUCT["id"]


FAKE_PRICE_TIER = {
    "active": True,
    "billing_scheme": "tiered",
    "created": 1386247539,
    "currency": "usd",
    "id": "price_tier21323",
    "livemode": False,
    "lookup_key": None,
    "metadata": {},
    "nickname": "New price name",
    "object": "price",
    "product": FAKE_PRODUCT["id"],
    "recurring": {
        "aggregate_usage": None,
        "interval": "month",
        "interval_count": 1,
        "trial_period_days": None,
        "usage_type": "licensed",
    },
    "tiers": [
        {
            "flat_amount": 4900,
            "flat_amount_decimal": "4900",
            "unit_amount": 1000,
            "unit_amount_decimal": "1000",
            "up_to": 5,
        },
        {
            "flat_amount": None,
            "flat_amount_decimal": None,
            "unit_amount": 900,
            "unit_amount_decimal": "900",
            "up_to": None,
        },
    ],
    "tiers_mode": "graduated",
    "transform_quantity": None,
    "type": "recurring",
    "unit_amount": None,
    "unit_amount_decimal": None,
}

FAKE_PRICE_METERED = {
    "active": True,
    "billing_scheme": "per_unit",
    "created": 1552632817,
    "currency": "usd",
    "id": "price_fakemetered",
    "livemode": False,
    "lookup_key": None,
    "metadata": {},
    "nickname": "Sum Metered Price",
    "object": "price",
    "product": FAKE_PRODUCT["id"],
    "recurring": {
        "aggregate_usage": "sum",
        "interval": "month",
        "interval_count": 1,
        "trial_period_days": None,
        "usage_type": "metered",
    },
    "tiers_mode": None,
    "transform_quantity": None,
    "type": "recurring",
    "unit_amount": 200,
    "unit_amount_decimal": "200",
}

FAKE_PRICE_ONETIME = {
    "active": True,
    "billing_scheme": "per_unit",
    "created": 1552632818,
    "currency": "usd",
    "id": "price_fakeonetime",
    "livemode": False,
    "lookup_key": None,
    "metadata": {},
    "nickname": "One-Time Price",
    "object": "price",
    "product": FAKE_PRODUCT["id"],
    "recurring": None,
    "tiers_mode": None,
    "transform_quantity": None,
    "type": "one_time",
    "unit_amount": 2000,
    "unit_amount_decimal": "2000",
}


class SubscriptionDict(StripeItem):
    def __init__(self, *args, **kwargs):
        """Match Stripe's behavior: return a stripe iterable on `subscription.items`."""
        super().__init__(*args, **kwargs)
        self["items"] = StripeList(self["items"])

    def __setattr__(self, name, value):
        if type(value) == datetime:
            value = datetime_to_unix(value)

        # Special case for price and plan
        if name == "price":
            for price in [
                FAKE_PRICE,
                FAKE_PRICE_II,
                FAKE_PRICE_TIER,
                FAKE_PRICE_METERED,
            ]:
                if value == price["id"]:
                    value = price
        elif name == "plan":
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
        "pause_collection": None,
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


FAKE_SUBSCRIPTION_ITEM_METERED = {
    "id": "si_JiphMAMFxZKW8s",
    "object": "subscription_item",
    "metadata": {},
    "billing_thresholds": "",
    "created": 1441907581,
    "plan": deepcopy(FAKE_PLAN_METERED),
    "price": deepcopy(FAKE_PRICE_METERED),
    "quantity": 1,
    "subscription": FAKE_SUBSCRIPTION_METERED["id"],
    "tax_rates": [],
}

FAKE_SUBSCRIPTION_ITEM_MULTI_PLAN = {
    "id": "si_JiphMAMFxZKW8s",
    "object": "subscription_item",
    "metadata": {},
    "billing_thresholds": "",
    "created": 1441907581,
    "plan": deepcopy(FAKE_PLAN),
    "price": deepcopy(FAKE_PRICE),
    "quantity": 1,
    "subscription": FAKE_SUBSCRIPTION_MULTI_PLAN["id"],
    "tax_rates": [],
}

FAKE_SUBSCRIPTION_ITEM_TAX_RATES = {
    "id": "si_JiphMAMFxZKW8s",
    "object": "subscription_item",
    "metadata": {},
    "billing_thresholds": "",
    "created": 1441907581,
    "plan": deepcopy(FAKE_PLAN_II),
    "price": deepcopy(FAKE_PRICE_II),
    "quantity": 1,
    "subscription": FAKE_SUBSCRIPTION_II["id"],
    "tax_rates": [
        {
            "id": "txr_fakefakefakefakefake0001",
            "object": "tax_rate",
            "active": True,
            "created": 1593225980,
            "description": None,
            "display_name": "VAT",
            "inclusive": True,
            "jurisdiction": "Example1",
            "livemode": False,
            "metadata": {"djstripe_test_fake_id": "txr_fakefakefakefakefake0001"},
            "percentage": 15.0,
        }
    ],
}


FAKE_SUBSCRIPTION_SCHEDULE = {
    "id": "sub_sched_1Hm7q6Fz0jfFqjGs2OxOSCzD",
    "object": "subscription_schedule",
    "canceled_at": None,
    "completed_at": None,
    "created": 1605056974,
    "current_phase": {},
    "customer": "cus_6lsBvm5rJ0zyHc",  # FAKE_CUSTOMER
    "default_settings": {
        "billing_cycle_anchor": "automatic",
        "billing_thresholds": None,
        "collection_method": "charge_automatically",
        "default_payment_method": None,
        "default_source": None,
        "invoice_settings": None,
        "transfer_data": None,
    },
    "end_behavior": "release",
    "livemode": False,
    "metadata": {},
    "phases": [
        {
            "add_invoice_items": [],
            "application_fee_percent": None,
            "billing_cycle_anchor": None,
            "billing_thresholds": None,
            "collection_method": None,
            "coupon": None,
            "default_payment_method": None,
            "default_tax_rates": [],
            "end_date": 1637195591,
            "invoice_settings": None,
            "plans": [
                {
                    "billing_thresholds": None,
                    "plan": FAKE_PLAN_II["id"],
                    "price": FAKE_PRICE_II["id"],
                    "quantity": None,
                    "tax_rates": [],
                }
            ],
            "prorate": True,
            "proration_behavior": "create_prorations",
            "start_date": 1605659591,
            "tax_percent": None,
            "transfer_data": None,
            "trial_end": None,
        }
    ],
    "released_at": None,
    "released_subscription": None,
    "renewal_interval": None,
    "status": "not_started",
    "subscription": FAKE_SUBSCRIPTION["id"],
}


FAKE_SHIPPING_RATE = load_fixture("shipping_rate_shr_fakefakefakefakefake0001.json")
FAKE_SHIPPING_RATE_WITH_TAX_CODE = load_fixture(
    "shipping_rate_shr_fakefakefakefakefake0002.json"
)


class Sources(object):
    def __init__(self, card_fakes):
        self.card_fakes = card_fakes

    def create(self, source, api_key=None):
        for fake_card in self.card_fakes:
            if fake_card["id"] == source:
                return fake_card

    def retrieve(self, id, expand=None):
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


# Customer with multiple subscriptions (all licensed usagetype)
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

FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE = deepcopy(FAKE_SUBSCRIPTION_METERED)
FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE["customer"] = FAKE_CUSTOMER_II["id"]


FAKE_SUBSCRIPTION_ITEM = {
    "id": "si_JiphMAMFxZKW8s",
    "object": "subscription_item",
    "metadata": {},
    "billing_thresholds": "",
    "created": 1441907581,
    "plan": deepcopy(FAKE_PLAN_METERED),
    "price": deepcopy(FAKE_PRICE_METERED),
    "quantity": 1,
    "subscription": FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE["id"],
    "tax_rates": [],
}


FAKE_INVOICE_METERED_SUBSCRIPTION = InvoiceDict(
    {
        "id": "in_1JGGM6JSZQVUcJYgpWqfBOIl",
        "livemode": False,
        "created": 1439425915,
        "metadata": {},
        "description": "",
        "amount_due": "1.05",
        "amount_paid": "1.05",
        "amount_remaining": "0.00",
        "application_fee_amount": None,
        "attempt_count": 1,
        "attempted": True,
        "auto_advance": False,
        "collection_method": "charge_automatically",
        "currency": "usd",
        "customer": FAKE_CUSTOMER_II["id"],
        "object": "invoice",
        "charge": None,
        "discount": None,
        "due_date": None,
        "ending_balance": 0,
        "lines": {
            "data": [
                {
                    "amount": 2000,
                    "id": FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE["id"],
                    "object": "line_item",
                    "currency": "usd",
                    "description": None,
                    "discountable": True,
                    "livemode": True,
                    "metadata": {},
                    "period": {"start": 1442111228, "end": 1444703228},
                    "plan": deepcopy(FAKE_PLAN_METERED),
                    "proration": False,
                    "quantity": 1,
                    "subscription": FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE["id"],
                    "subscription_item": FAKE_SUBSCRIPTION_ITEM["id"],
                    "type": "subscription",
                }
            ],
            "total_count": 1,
            "object": "list",
            "url": "/v1/invoices/in_1JGGM6JSZQVUcJYgpWqfBOIl/lines",
        },
        "next_payment_attempt": None,
        "number": "84DE1540-0004",
        "paid": True,
        "period_end": 1439424571,
        "period_start": 1436746171,
        "receipt_number": None,
        "starting_balance": 0,
        "statement_descriptor": None,
        "subscription": FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE["id"],
        "subtotal": "1.00",
        "tax": None,
        "tax_percent": None,
        "total": "1.00",
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

FAKE_TAX_ID = load_fixture("tax_id_txi_fakefakefakefakefake0001.json")


FAKE_EVENT_TAX_ID_CREATED = {
    "id": "evt_16YKQi2eZvKYlo2CT2oe5ff3",
    "object": "event",
    "api_version": "2020-08-27",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_TAX_ID)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_ZoH080M8fny6yR",
    "type": "customer.tax_id.created",
}

FAKE_TAX_ID_UPDATED = deepcopy(FAKE_TAX_ID)
FAKE_TAX_ID_UPDATED["verification"] = {
    "status": "verified",
    "verified_address": None,
    "verified_name": "Test",
}

FAKE_EVENT_TAX_ID_UPDATED = {
    "id": "evt_1J6Fy3JSZQVUcJYgnddjnMzx",
    "object": "event",
    "api_version": "2020-08-27",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_TAX_ID_UPDATED)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_ZoH080M8fny6yR",
    "type": "customer.tax_id.updated",
}

FAKE_EVENT_TAX_ID_DELETED = deepcopy(FAKE_EVENT_TAX_ID_UPDATED)
FAKE_EVENT_TAX_ID_DELETED["type"] = "customer.tax_id.deleted"

FAKE_TAX_CODE = load_fixture("tax_code_txcd_fakefakefakefakefake0001.json")

FAKE_INVOICEITEM = {
    "id": "ii_16XVTY2eZvKYlo2Cxz5n3RaS",
    "object": "invoiceitem",
    "amount": 2000,
    "currency": "usd",
    "customer": FAKE_CUSTOMER_II["id"],
    "date": 1439033216,
    "description": "One-time setup fee",
    "discountable": True,
    "discounts": [],
    "invoice": FAKE_INVOICE_II["id"],
    "livemode": False,
    "metadata": {"key1": "value1", "key2": "value2"},
    "period": {"start": 1439033216, "end": 1439033216},
    "plan": None,
    "price": None,
    "proration": False,
    "quantity": None,
    "subscription": None,
    "subscription_item": None,
    "tax_rates": [],
    "unit_amount": 2000,
    "unit_amount_decimal": "2000",
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
    "discounts": [],
    "invoice": FAKE_INVOICE["id"],
    "livemode": False,
    "metadata": {"key1": "value1", "key2": "value2"},
    "period": {"start": 1439033216, "end": 1439033216},
    "plan": None,
    "price": None,
    "proration": False,
    "quantity": None,
    "subscription": None,
    "subscription_item": None,
    "tax_rates": [],
    "unit_amount": 2000,
    "unit_amount_decimal": "2000",
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
    "discounts": [],
    "invoice": FAKE_INVOICE_II["id"],
    "livemode": False,
    "metadata": {"key1": "value1", "key2": "value2"},
    "period": {"start": 1439033216, "end": 1439033216},
    "plan": None,
    "price": None,
    "proration": False,
    "quantity": None,
    "subscription": None,
    "subscription_item": None,
    "tax_rates": [FAKE_TAX_RATE_EXAMPLE_1_VAT],
    "unit_amount": 2000,
    "unit_amount_decimal": "2000",
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
    "destination": FAKE_STANDARD_ACCOUNT["id"],
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

FAKE_TRANSFER_WITH_1_REVERSAL = {
    "id": "tr_16Y9BK2eZvKYlo2CR0ySu1BA",
    "object": "transfer",
    "amount": 100,
    "amount_reversed": 0,
    "application_fee_amount": None,
    "balance_transaction": deepcopy(FAKE_BALANCE_TRANSACTION_II),
    "created": 1439185846,
    "currency": "usd",
    "description": "Test description - 1439185984",
    "destination": FAKE_STANDARD_ACCOUNT["id"],
    "destination_payment": "py_16Y9BKFso9hLaeLueFmWAYUi",
    "livemode": False,
    "metadata": {},
    "recipient": None,
    "reversals": {
        "object": "list",
        "total_count": 1,
        "has_more": False,
        "url": "/v1/transfers/tr_16Y9BK2eZvKYlo2CR0ySu1BA/reversals",
        "data": [
            {
                "id": "trr_1J5UlFJSZQVUcJYgb38m1OZO",
                "object": "transfer_reversal",
                "amount": 20,
                "balance_transaction": deepcopy(FAKE_BALANCE_TRANSACTION_II),
                "created": 1624449653,
                "currency": "usd",
                "destination_payment_refund": "pyr_1J5UlFR44xKqawmIBvFa6gW9",
                "metadata": {},
                "source_refund": None,
                "transfer": deepcopy(FAKE_TRANSFER),
            }
        ],
    },
    "reversed": False,
    "source_transaction": None,
    "source_type": "bank_account",
}


FAKE_USAGE_RECORD = {
    "id": "mbur_1JPJz2JSZQVUcJYgK4otTE2V",
    "livemode": False,
    "object": "usage_record",
    "quantity": 100,
    "subscription_item": FAKE_SUBSCRIPTION_ITEM["id"],
    "timestamp": 1629174774,
    "action": "increment",
}


class UsageRecordSummaryDict(StripeItem):
    pass


FAKE_USAGE_RECORD_SUMMARY = UsageRecordSummaryDict(
    load_fixture("usage_record_summary_sis_fakefakefakefakefake0001.json")
)


class WebhookEndpointDict(StripeItem):
    pass


FAKE_WEBHOOK_ENDPOINT_1 = WebhookEndpointDict(
    load_fixture("webhook_endpoint_fake0001.json")
)


FAKE_ACCOUNT = {
    "id": "acct_1032D82eZvKYlo2C",
    "object": "account",
    "business_profile": {
        "name": "dj-stripe",
        "support_email": "djstripe@example.com",
        "support_phone": None,
        "support_url": "https://djstripe.com/support/",
        "url": "https://djstripe.com",
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
                "expires_at": 1850134074,
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
                "expires_at": 1850134074,
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

FAKE_EVENT_FILE_CREATED = {
    "id": "evt_1J5TusR44xKqawmIQVXSrGyf",
    "object": "event",
    "api_version": "2020-08-27",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_FILEUPLOAD_ICON)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_sTSstDDIOpKi2w",
    "type": "file.created",
}


FAKE_EVENT_ACCOUNT_APPLICATION_DEAUTHORIZED = dict(
    load_fixture("event_account_application_deauthorized.json")
)

FAKE_EVENT_ACCOUNT_APPLICATION_AUTHORIZED = dict(
    load_fixture("event_account_application_authorized.json")
)

FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_CREATED = dict(
    load_fixture("event_external_account_bank_account_created.json")
)
FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_CREATED = dict(
    load_fixture("event_external_account_card_created.json")
)

FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_DELETED = dict(
    load_fixture("event_external_account_bank_account_deleted.json")
)
FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_DELETED = dict(
    load_fixture("event_external_account_card_deleted.json")
)

FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_BANK_ACCOUNT_UPDATED = dict(
    load_fixture("event_external_account_bank_account_updated.json")
)
FAKE_EVENT_ACCOUNT_EXTERNAL_ACCOUNT_CARD_UPDATED = dict(
    load_fixture("event_external_account_card_updated.json")
)

FAKE_EVENT_STANDARD_ACCOUNT_UPDATED = dict(
    load_fixture("event_account_updated_standard.json")
)


FAKE_EVENT_EXPRESS_ACCOUNT_UPDATED = dict(
    load_fixture("event_account_updated_express.json")
)

FAKE_EVENT_CUSTOM_ACCOUNT_UPDATED = dict(
    load_fixture("event_account_updated_custom.json")
)

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
    "api_version": "2016-03-07; orders_beta=v3",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_CUSTOMER)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6l38DHch3whaDj",
    "type": "customer.created",
}

FAKE_EVENT_CUSTOMER_UPDATED = deepcopy(FAKE_EVENT_CUSTOMER_CREATED)
FAKE_EVENT_CUSTOMER_UPDATED["type"] = "customer.updated"


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
    "data": {"object": deepcopy(FAKE_DISPUTE_I)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6lsB7hkicwhaDj",
    "type": "charge.dispute.created",
}


FAKE_EVENT_DISPUTE_FUNDS_WITHDRAWN = {
    "id": "evt_1JAyTxJSZQVUcJYgNk1Jqu8o",
    "object": "event",
    "api_version": "2020-08-27",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_DISPUTE_II)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6lsB7hkicwhaDj",
    "type": "charge.dispute.funds_withdrawn",
}


FAKE_EVENT_DISPUTE_UPDATED = {
    "id": "evt_1JAyTxJSZQVUcJYgNk1Jqu8o",
    "object": "event",
    "api_version": "2020-08-27",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_DISPUTE_III)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6lsB7hkicwhaDj",
    "type": "charge.dispute.funds_withdrawn",
}

FAKE_EVENT_DISPUTE_CLOSED = {
    "id": "evt_1JAyTxJSZQVUcJYgNk1Jqu8o",
    "object": "event",
    "api_version": "2020-08-27",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_DISPUTE_IV)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6lsB7hkicwhaDj",
    "type": "charge.dispute.closed",
}

FAKE_EVENT_DISPUTE_FUNDS_REINSTATED_FULL = {
    "id": "evt_1JAyTxJSZQVUcJYgNk1Jqu8o",
    "object": "event",
    "api_version": "2020-08-27",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_DISPUTE_V_FULL)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6lsB7hkicwhaDj",
    "type": "charge.dispute.funds_reinstated",
}

FAKE_EVENT_DISPUTE_FUNDS_REINSTATED_PARTIAL = {
    "id": "evt_1JAyTxJSZQVUcJYgNk1Jqu8o",
    "object": "event",
    "api_version": "2020-08-27",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_DISPUTE_V_PARTIAL)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6lsB7hkicwhaDj",
    "type": "charge.dispute.funds_reinstated",
}

FAKE_EVENT_SESSION_COMPLETED = {
    "id": "evt_1JAyTxJSZQVUcJYgNk1Jqu8o",
    "object": "event",
    "api_version": "2020-08-27",
    "created": 1439229084,
    "data": {"object": deepcopy(FAKE_SESSION_I)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": "req_6lsB7hkicwhaDj",
    "type": "checkout.session.completed",
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

FAKE_EVENT_PRICE_CREATED = {
    "id": "evt_1HlZWCFz0jfFqjGsXOiPW10r",
    "object": "event",
    "api_version": "2020-03-02",
    "created": 1604925044,
    "data": {"object": deepcopy(FAKE_PRICE)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": {"id": "req_Nq7dDuP0HRrqcP", "idempotency_key": None},
    "type": "price.created",
}

FAKE_EVENT_PRICE_UPDATED = {
    "id": "evt_1HlZbxFz0jfFqjGsZwiHHf7h",
    "object": "event",
    "api_version": "2020-03-02",
    "created": 1604925401,
    "data": {
        "object": FAKE_PRICE,
        "previous_attributes": {"unit_amount": 2000, "unit_amount_decimal": "2000"},
    },
    "livemode": False,
    "pending_webhooks": 0,
    "request": {"id": "req_78pnxbwPMvOIwe", "idempotency_key": None},
    "type": "price.updated",
}

FAKE_EVENT_PRICE_DELETED = deepcopy(FAKE_EVENT_PRICE_CREATED)
FAKE_EVENT_PRICE_DELETED.update(
    {"id": "evt_1HlZelFz0jfFqjGs0F4BML2l", "type": "price.deleted"}
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

FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED = {
    "id": "evt_1Hm7q6Fz0jfFqjGsJSG4N91w",
    "object": "event",
    "api_version": "2020-03-02",
    "created": 1605056974,
    "data": {"object": deepcopy(FAKE_SUBSCRIPTION_SCHEDULE)},
    "livemode": False,
    "pending_webhooks": 0,
    "request": {
        "id": "req_Pttj3aW5RJwees",
        "idempotency_key": "d2a77191-cc07-4c60-abab-5fb11357bd63",
    },
    "type": "subscription_schedule.created",
}
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED["data"]["object"]["status"] = "active"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED["data"]["object"]["current_phase"][
    "start_data"
] = 1602464974
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED["data"]["object"]["current_phase"][
    "end_data"
] = 1605056974


FAKE_EVENT_SUBSCRIPTION_SCHEDULE_UPDATED = deepcopy(
    FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED
)
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_UPDATED["id"] = "sub_sched_1Hm86MFz0jfFqjGsc5iEdZee"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_UPDATED["type"] = "subscription_schedule.updated"


FAKE_EVENT_SUBSCRIPTION_SCHEDULE_RELEASED = deepcopy(
    FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED
)
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_RELEASED["id"] = "evt_1Hm878Fz0jfFqjGsClU9gE79"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_RELEASED["type"] = "subscription_schedule.released"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_RELEASED["data"]["object"]["released_at"] = 1605058030
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_RELEASED["data"]["object"]["status"] = "released"

FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CANCELED = deepcopy(
    FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED
)
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CANCELED["id"] = "evt_1Hm80YFz0jfFqjGs7kKvT7RE"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CANCELED["type"] = "subscription_schedule.canceled"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CANCELED["data"]["object"]["canceled_at"] = 1605057622
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CANCELED["data"]["object"]["status"] = "canceled"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CANCELED["data"]["previous_attributes"] = {
    "released_at": None,
    "status": "not_started",
}


FAKE_EVENT_SUBSCRIPTION_SCHEDULE_COMPLETED = deepcopy(
    FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED
)
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_COMPLETED["id"] = "evt_1Hm80YFz0jfFqjGs7kKvT7RE"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_COMPLETED["type"] = "subscription_schedule.completed"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_COMPLETED["data"]["object"][
    "completed_at"
] = 1605057622
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_COMPLETED["data"]["object"]["status"] = "completed"


# would get emmited 7 days before the scheduled end_date
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_EXPIRING = deepcopy(
    FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED
)
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_EXPIRING["id"] = "evt_1Hm80YFz0jfFqjGs7kKvT7RE"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_EXPIRING["type"] = "subscription_schedule.expiring"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_EXPIRING["created"] = 1602464900


FAKE_EVENT_SUBSCRIPTION_SCHEDULE_ABORTED = deepcopy(
    FAKE_EVENT_SUBSCRIPTION_SCHEDULE_CREATED
)
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_ABORTED["id"] = "evt_1Hm80YFz0jfFqjGs7kKvT7RE"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_ABORTED["type"] = "subscription_schedule.aborted"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_ABORTED["data"]["object"]["canceled_at"] = 1605057622
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_ABORTED["data"]["object"]["status"] = "canceled"
FAKE_EVENT_SUBSCRIPTION_SCHEDULE_ABORTED["data"]["previous_attributes"] = {
    "released_at": None,
    "status": "not_started",
}
