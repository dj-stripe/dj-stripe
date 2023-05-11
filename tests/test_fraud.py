"""
dj-stripe tests for the fraud.py module
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.test.testcases import TestCase

from djstripe.models.fraud import Review

from . import (
    FAKE_ACCOUNT,
    FAKE_BALANCE_TRANSACTION,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_INVOICE,
    FAKE_INVOICEITEM,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PLAN,
    FAKE_PRODUCT,
    FAKE_REVIEW_WARNING,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_ITEM,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db
from .conftest import CreateAccountMixin


class TestReview(CreateAccountMixin, AssertStripeFksMixin, TestCase):
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_CHARGE),
        autospec=True,
    )
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_ITEM),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    def test_sync_from_stripe_data(
        self,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        payment_intent_retrieve_mock,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        customer_retrieve_mock,
        account_retrieve_mock,
    ):
        fake_review_warning_data = deepcopy(FAKE_REVIEW_WARNING)

        fake_review_warning = Review.sync_from_stripe_data(fake_review_warning_data)

        self.assertEqual(fake_review_warning.id, fake_review_warning_data["id"])

        self.assertEqual(
            fake_review_warning.charge.id,
            fake_review_warning_data["charge"]["id"],
        )
        self.assertEqual(
            fake_review_warning.payment_intent.id,
            fake_review_warning_data["payment_intent"]["id"],
        )

        self.assert_fks(
            fake_review_warning,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
                "djstripe.Invoice.default_payment_method",
                "djstripe.PaymentIntent.upcominginvoice (related name)",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.Subscription.default_payment_method",
                "djstripe.Subscription.default_source",
                "djstripe.Subscription.pending_setup_intent",
                "djstripe.Product.default_price",
                "djstripe.Subscription.schedule",
                "djstripe.Invoice.default_source",
                "djstripe.Charge.latest_upcominginvoice (related name)",
                "djstripe.Charge.application_fee",
                "djstripe.Charge.dispute",
                "djstripe.Charge.on_behalf_of",
                "djstripe.Charge.source_transfer",
                "djstripe.Charge.transfer",
            },
        )

    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_CHARGE),
        autospec=True,
    )
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_ITEM),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    def test___str__(
        self,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        payment_intent_retrieve_mock,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        customer_retrieve_mock,
        account_retrieve_mock,
    ):
        fake_review_warning_data = deepcopy(FAKE_REVIEW_WARNING)

        fake_review_warning = Review.sync_from_stripe_data(fake_review_warning_data)

        self.assertEqual(str(fake_review_warning), "(True) for $20.00 USD (Succeeded))")
