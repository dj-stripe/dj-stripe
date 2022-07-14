"""
dj-stripe BalanceTransaction model tests
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.test.testcases import TestCase

from djstripe import models
from djstripe.enums import BalanceTransactionStatus

from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_INVOICE,
    FAKE_INVOICEITEM,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PLAN,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_ITEM,
)

pytestmark = pytest.mark.django_db


class TestBalanceTransactionStr:
    @pytest.mark.parametrize("transaction_status", BalanceTransactionStatus.__members__)
    def test___str__(self, transaction_status):
        modified_balance_transaction = deepcopy(FAKE_BALANCE_TRANSACTION)
        modified_balance_transaction["status"] = transaction_status

        balance_transaction = models.BalanceTransaction.sync_from_stripe_data(
            modified_balance_transaction
        )
        assert (
            str(balance_transaction)
            == f"$20.00 USD ({BalanceTransactionStatus.humanize(modified_balance_transaction['status'])})"
        )


class TestBalanceTransactionSourceClass:
    @pytest.mark.parametrize("transaction_type", ["card", "payout", "refund"])
    def test_get_source_class_success(self, transaction_type):
        modified_balance_transaction = deepcopy(FAKE_BALANCE_TRANSACTION)
        modified_balance_transaction["type"] = transaction_type

        balance_transaction = models.BalanceTransaction.sync_from_stripe_data(
            modified_balance_transaction
        )
        assert balance_transaction.get_source_class() is getattr(
            models, transaction_type.capitalize(), None
        )

    @pytest.mark.parametrize("transaction_type", ["network_cost", "payment_refund"])
    def test_get_source_class_failure(self, transaction_type):

        modified_balance_transaction = deepcopy(FAKE_BALANCE_TRANSACTION)
        modified_balance_transaction["type"] = transaction_type

        balance_transaction = models.BalanceTransaction.sync_from_stripe_data(
            modified_balance_transaction
        )
        with pytest.raises(LookupError):
            balance_transaction.get_source_class()


class TestBalanceTransaction(TestCase):
    @patch(
        "stripe.Invoice.retrieve",
        return_value=deepcopy(FAKE_INVOICE),
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
        "stripe.PaymentIntent.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_CHARGE),
    )
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    def test_sync_from_stripe_data(
        self,
        subscription_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        charge_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        balance_transaction_retrieve_mock,
        customer_retrieve_mock,
        invoice_retrieve_mock,
    ):

        balance_transaction = models.BalanceTransaction.sync_from_stripe_data(
            deepcopy(FAKE_BALANCE_TRANSACTION)
        )

        balance_transaction_retrieve_mock.assert_not_called()

        assert balance_transaction.type == FAKE_BALANCE_TRANSACTION["type"]
        assert balance_transaction.amount == FAKE_BALANCE_TRANSACTION["amount"]
        assert balance_transaction.status == FAKE_BALANCE_TRANSACTION["status"]

    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve",
        return_value=deepcopy(FAKE_INVOICE),
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
        "stripe.PaymentIntent.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_CHARGE),
    )
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_SUBSCRIPTION_ITEM),
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    def test_get_source_instance(
        self,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        charge_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        balance_transaction_retrieve_mock,
        customer_retrieve_mock,
        invoice_retrieve_mock,
        invoiceitem_retrieve_mock,
    ):

        balance_transaction = models.BalanceTransaction.sync_from_stripe_data(
            deepcopy(FAKE_BALANCE_TRANSACTION)
        )
        charge = models.Charge.sync_from_stripe_data(deepcopy(FAKE_CHARGE))
        assert balance_transaction.get_source_instance() == charge

    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve",
        return_value=deepcopy(FAKE_INVOICE),
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
        "stripe.PaymentIntent.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_CHARGE),
    )
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_SUBSCRIPTION_ITEM),
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    def test_get_stripe_dashboard_url(
        self,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        charge_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        balance_transaction_retrieve_mock,
        customer_retrieve_mock,
        invoice_retrieve_mock,
        invoiceitem_retrieve_mock,
    ):

        balance_transaction = models.BalanceTransaction.sync_from_stripe_data(
            deepcopy(FAKE_BALANCE_TRANSACTION)
        )
        charge = models.Charge.sync_from_stripe_data(deepcopy(FAKE_CHARGE))
        assert (
            balance_transaction.get_stripe_dashboard_url()
            == charge.get_stripe_dashboard_url()
        )
