"""
dj-stripe PaymentIntent Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
import stripe
from django.test import TestCase

from djstripe.models import PaymentIntent

from . import (
    FAKE_ACCOUNT,
    FAKE_BALANCE_TRANSACTION,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_INVOICE,
    FAKE_PAYMENT_INTENT_DESTINATION_CHARGE,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PAYMENT_METHOD_I,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


def _get_fake_payment_intent_destination_charge_no_customer():
    FAKE_PAYMENT_INTENT_DESTINATION_CHARGE_NO_CUSTOMER = deepcopy(
        FAKE_PAYMENT_INTENT_DESTINATION_CHARGE
    )
    FAKE_PAYMENT_INTENT_DESTINATION_CHARGE_NO_CUSTOMER["customer"] = None
    return FAKE_PAYMENT_INTENT_DESTINATION_CHARGE_NO_CUSTOMER


def _get_fake_payment_intent_i_no_customer():
    FAKE_PAYMENT_INTENT_I_NO_CUSTOMER = deepcopy(FAKE_PAYMENT_INTENT_I)
    FAKE_PAYMENT_INTENT_I_NO_CUSTOMER["customer"] = None
    return FAKE_PAYMENT_INTENT_I_NO_CUSTOMER


class TestStrPaymentIntent:

    #
    # Helpers
    #

    @pytest.mark.parametrize(
        "fake_intent_data, has_account, has_customer",
        [
            (FAKE_PAYMENT_INTENT_I, False, True),
            (FAKE_PAYMENT_INTENT_DESTINATION_CHARGE, True, True),
            (_get_fake_payment_intent_destination_charge_no_customer(), True, False),
            (_get_fake_payment_intent_i_no_customer(), False, False),
        ],
    )
    def test___str__(self, fake_intent_data, has_account, has_customer, monkeypatch):
        def mock_customer_get(*args, **kwargs):
            """Monkeypatched stripe.Customer.retrieve"""
            return deepcopy(FAKE_CUSTOMER)

        def mock_account_get(*args, **kwargs):
            """Monkeypatched stripe.Account.retrieve"""
            data = deepcopy(FAKE_ACCOUNT)
            # Otherwise Account.api_retrieve will invoke File.api_retrieve...
            data["settings"]["branding"] = {}
            return data

        def mock_payment_method_get(*args, **kwargs):
            """Monkeypatched stripe.PaymentMethod.retrieve"""
            return deepcopy(FAKE_PAYMENT_METHOD_I)

        def mock_invoice_get(*args, **kwargs):
            """Monkeypatched stripe.Invoice.retrieve"""
            return deepcopy(FAKE_INVOICE)

        def mock_subscription_get(*args, **kwargs):
            """Monkeypatched stripe.Subscription.retrieve"""
            return deepcopy(FAKE_SUBSCRIPTION)

        def mock_balance_transaction_get(*args, **kwargs):
            """Monkeypatched stripe.BalanceTransaction.retrieve"""
            return deepcopy(FAKE_BALANCE_TRANSACTION)

        def mock_product_get(*args, **kwargs):
            """Monkeypatched stripe.Product.retrieve"""
            return deepcopy(FAKE_PRODUCT)

        def mock_charge_get(*args, **kwargs):
            """Monkeypatched stripe.Charge.retrieve"""
            return deepcopy(FAKE_CHARGE)

        # monkeypatch stripe.Product.retrieve, stripe.Price.retrieve, stripe.PaymentMethod.retrieve, and stripe.PaymentIntent.retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Account, "retrieve", mock_account_get)
        monkeypatch.setattr(stripe.Customer, "retrieve", mock_customer_get)
        monkeypatch.setattr(stripe.PaymentMethod, "retrieve", mock_payment_method_get)

        # because of Reverse o2o field sync due to PaymentIntent.sync_from_stripe_data..
        monkeypatch.setattr(stripe.Invoice, "retrieve", mock_invoice_get)
        monkeypatch.setattr(stripe.Subscription, "retrieve", mock_subscription_get)
        monkeypatch.setattr(
            stripe.BalanceTransaction, "retrieve", mock_balance_transaction_get
        )
        monkeypatch.setattr(stripe.Product, "retrieve", mock_product_get)
        monkeypatch.setattr(stripe.Charge, "retrieve", mock_charge_get)

        pi = PaymentIntent.sync_from_stripe_data(fake_intent_data)
        assert pi

        # due to reverse o2o sync invoice should also get created
        if fake_intent_data.get("invoice"):
            assert pi.invoice is not None

        if has_account and has_customer:

            assert (
                str(pi)
                == "$1,902.00 USD (The funds are in your account.) for dj-stripe by Michael Smith"
            )

        elif has_account and not has_customer:

            assert (
                str(pi)
            ) == "$1,902.00 USD for dj-stripe. The funds are in your account."

        elif has_customer and not has_account:

            assert (
                str(pi)
            ) == "$20.00 USD by Michael Smith. The funds are in your account."
        elif not has_customer and not has_account:

            assert str(pi) == "$20.00 USD (The funds are in your account.)"


class PaymentIntentTest(AssertStripeFksMixin, TestCase):
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    def test_sync_from_stripe_data(
        self,
        invoice_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):

        payment_intent = PaymentIntent.sync_from_stripe_data(
            deepcopy(FAKE_PAYMENT_INTENT_I)
        )

        self.assert_fks(
            payment_intent,
            expected_blank_fks={
                "djstripe.Charge.latest_upcominginvoice (related name)",
                "djstripe.Charge.application_fee",
                "djstripe.Charge.dispute",
                "djstripe.Charge.on_behalf_of",
                "djstripe.Charge.source_transfer",
                "djstripe.Charge.transfer",
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
                "djstripe.Invoice.default_payment_method",
                "djstripe.Invoice.default_source",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.PaymentIntent.upcominginvoice (related name)",
                "djstripe.Subscription.default_payment_method",
                "djstripe.Subscription.default_source",
                "djstripe.Subscription.pending_setup_intent",
                "djstripe.Subscription.schedule",
            },
        )

        assert payment_intent
        self.assertIsNotNone(payment_intent.invoice)

    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    def test_status_enum(
        self,
        invoice_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)

        for status in (
            "requires_payment_method",
            "requires_confirmation",
            "requires_action",
            "processing",
            "requires_capture",
            "canceled",
            "succeeded",
        ):
            fake_payment_intent["status"] = status
            payment_intent = PaymentIntent.sync_from_stripe_data(fake_payment_intent)

            # trigger model field validation (including enum value choices check)
            assert payment_intent
            payment_intent.full_clean()

    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    def test_canceled_intent(
        self,
        invoice_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)

        fake_payment_intent["status"] = "canceled"
        fake_payment_intent["canceled_at"] = 1567524169

        for reason in (
            None,
            "duplicate",
            "fraudulent",
            "requested_by_customer",
            "abandoned",
            "failed_invoice",
            "void_invoice",
            "automatic",
        ):
            fake_payment_intent["cancellation_reason"] = reason
            payment_intent = PaymentIntent.sync_from_stripe_data(fake_payment_intent)
            assert payment_intent

            if reason is None:
                # enums nulls are coerced to "" by StripeModel._stripe_object_to_record
                self.assertEqual(payment_intent.cancellation_reason, "")
            else:
                self.assertEqual(payment_intent.cancellation_reason, reason)

            # trigger model field validation (including enum value choices check)
            payment_intent.full_clean()
