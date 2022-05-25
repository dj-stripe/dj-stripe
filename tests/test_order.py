"""
dj-stripe Order model tests
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.test import TestCase

from djstripe.models import Order

from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_INVOICE,
    FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT,
    FAKE_ORDER_WITH_CUSTOMER_WITHOUT_PAYMENT_INTENT,
    FAKE_ORDER_WITHOUT_CUSTOMER_WITH_PAYMENT_INTENT,
    FAKE_ORDER_WITHOUT_CUSTOMER_WITHOUT_PAYMENT_INTENT,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PAYMENT_METHOD_I,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


class TestOrder(AssertStripeFksMixin, TestCase):
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
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
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
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        default_expected_blank_fks = {
            "djstripe.Customer.coupon",
            "djstripe.Customer.default_payment_method",
            "djstripe.Customer.subscriber",
            "djstripe.Charge.latest_upcominginvoice (related name)",
            "djstripe.Charge.application_fee",
            "djstripe.Charge.dispute",
            "djstripe.Charge.on_behalf_of",
            "djstripe.Charge.source_transfer",
            "djstripe.Charge.transfer",
            "djstripe.Invoice.default_payment_method",
            "djstripe.Invoice.default_source",
            "djstripe.Subscription.default_payment_method",
            "djstripe.Subscription.default_source",
            "djstripe.Subscription.pending_setup_intent",
            "djstripe.Subscription.schedule",
            "djstripe.PaymentIntent.on_behalf_of",
            "djstripe.PaymentIntent.payment_method",
            "djstripe.PaymentIntent.upcominginvoice (related name)",
        }
        # Ensure Order objects with Customer and PaymentIntent data sync correctly
        order = Order.sync_from_stripe_data(
            deepcopy(FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT)
        )
        self.assertEqual(order.payment_intent.id, FAKE_PAYMENT_INTENT_I["id"])
        self.assertEqual(order.customer.id, FAKE_CUSTOMER["id"])

        self.assert_fks(order, expected_blank_fks=default_expected_blank_fks)

        # Ensure Order objects with Customer and NO PaymentIntent data sync correctly
        order = Order.sync_from_stripe_data(
            deepcopy(FAKE_ORDER_WITH_CUSTOMER_WITHOUT_PAYMENT_INTENT)
        )
        self.assertEqual(order.payment_intent, None)
        self.assertEqual(order.customer.id, FAKE_CUSTOMER["id"])

        self.assert_fks(
            order,
            expected_blank_fks=default_expected_blank_fks
            | {
                "djstripe.Order.payment_intent",
            },
        )

        # Ensure Order objects with NO Customer and PaymentIntent data sync correctly
        order = Order.sync_from_stripe_data(
            deepcopy(FAKE_ORDER_WITHOUT_CUSTOMER_WITH_PAYMENT_INTENT)
        )
        self.assertEqual(order.payment_intent.id, FAKE_PAYMENT_INTENT_I["id"])
        self.assertEqual(order.customer, None)

        self.assert_fks(
            order,
            expected_blank_fks=default_expected_blank_fks
            | {
                "djstripe.Order.customer",
            },
        )

        # Ensure Order objects without Customer and without PaymentIntent data sync correctly
        order = Order.sync_from_stripe_data(
            deepcopy(FAKE_ORDER_WITHOUT_CUSTOMER_WITHOUT_PAYMENT_INTENT)
        )
        self.assertEqual(order.payment_intent, None)
        self.assertEqual(order.customer, None)

        self.assert_fks(
            order,
            expected_blank_fks=default_expected_blank_fks
            | {
                "djstripe.Order.customer",
                "djstripe.Order.payment_intent",
            },
        )
