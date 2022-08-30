"""
dj-stripe Order model tests
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
import stripe
from django.test import TestCase

from djstripe.enums import OrderStatus
from djstripe.models import Order
from djstripe.settings import djstripe_settings

from . import (
    FAKE_ACCOUNT,
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
    FAKE_PLATFORM_ACCOUNT,
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
        assert order
        self.assertEqual(order.payment_intent.id, FAKE_PAYMENT_INTENT_I["id"])
        self.assertEqual(order.customer.id, FAKE_CUSTOMER["id"])

        self.assert_fks(order, expected_blank_fks=default_expected_blank_fks)

        # Ensure Order objects with Customer and NO PaymentIntent data sync correctly
        order = Order.sync_from_stripe_data(
            deepcopy(FAKE_ORDER_WITH_CUSTOMER_WITHOUT_PAYMENT_INTENT)
        )
        assert order
        assert order.payment_intent is None
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
        assert order
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
        assert order
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

    def test__manipulate_stripe_object_hook(self):
        order_data = deepcopy(FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT)

        # Remove "payment_intent" key from order_data dictionary
        del order_data["payment_intent"]

        # assert "payment_intent" key is removed from the data dictionary
        self.assertTrue("payment_intent" not in order_data)

        # Invoke _manipulate_stripe_object_hook
        modified_order_data = Order._manipulate_stripe_object_hook(order_data)

        # assert "payment_intent" key gets added to the data dictionary
        self.assertTrue("payment_intent" in modified_order_data)
        self.assertEqual(
            modified_order_data["payment_intent"],
            order_data["payment"]["payment_intent"],
        )


class TestOrderStr:
    @pytest.mark.parametrize(
        "order_status",
        [
            OrderStatus.open,
            OrderStatus.canceled,
            OrderStatus.submitted,
            OrderStatus.complete,
            OrderStatus.processing,
        ],
    )
    def test___str__(self, order_status, monkeypatch):
        def mock_customer_get(*args, **kwargs):
            """Monkeypatched stripe.Customer.retrieve"""
            return deepcopy(FAKE_CUSTOMER)

        def mock_account_get(*args, **kwargs):
            """Monkeypatched stripe.Account.retrieve"""
            data = deepcopy(FAKE_ACCOUNT)
            # Otherwise Account.api_retrieve will invoke File.api_retrieve...
            data["settings"]["branding"] = {}
            return data

        def mock_payment_intent_get(*args, **kwargs):
            """Monkeypatched stripe.PaymentIntent.retrieve"""
            return deepcopy(FAKE_PAYMENT_INTENT_I)

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

        # monkeypatch stripe.Product.retrieve, stripe.Price.retrieve, stripe.PaymentIntent.retrieve, stripe.PaymentMethod.retrieve, and stripe.PaymentIntent.retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Account, "retrieve", mock_account_get)
        monkeypatch.setattr(stripe.Customer, "retrieve", mock_customer_get)
        monkeypatch.setattr(stripe.PaymentIntent, "retrieve", mock_payment_intent_get)
        monkeypatch.setattr(stripe.PaymentMethod, "retrieve", mock_payment_method_get)

        # because of Reverse o2o field sync due to PaymentIntent.sync_from_stripe_data..
        monkeypatch.setattr(stripe.Invoice, "retrieve", mock_invoice_get)
        monkeypatch.setattr(stripe.Subscription, "retrieve", mock_subscription_get)
        monkeypatch.setattr(
            stripe.BalanceTransaction, "retrieve", mock_balance_transaction_get
        )
        monkeypatch.setattr(stripe.Product, "retrieve", mock_product_get)
        monkeypatch.setattr(stripe.Charge, "retrieve", mock_charge_get)

        order_data = deepcopy(FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT)
        order_data["status"] = order_status

        order = Order.sync_from_stripe_data(order_data)

        if order_status in (OrderStatus.open, OrderStatus.canceled):
            assert str(order) == f"Created on 07/10/2019 ({order_status})"

        elif order_status in (
            OrderStatus.submitted,
            OrderStatus.complete,
            OrderStatus.processing,
        ):

            assert str(order) == f"Placed on 07/10/2019 ({order_status})"


class TestOrderMethods:
    @pytest.mark.parametrize("stripe_account", (None, "acct_fakefakefakefake001"))
    @pytest.mark.parametrize(
        "api_key, expected_api_key",
        (
            (None, djstripe_settings.STRIPE_SECRET_KEY),
            ("sk_fakefakefake01", "sk_fakefakefake01"),
        ),
    )
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
    @patch(
        "stripe.Order.cancel",
    )
    def test_cancel(
        self,
        order_cancel_mock,
        invoice_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        api_key,
        expected_api_key,
        stripe_account,
    ):
        fake_order = deepcopy(FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT)

        fake_order_cancel = deepcopy(FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT)
        fake_order_cancel["status"] = "canceled"
        order_cancel_mock.return_value = fake_order_cancel

        order = Order.sync_from_stripe_data(fake_order)
        assert order

        # Cancel the order
        cancelled_order = order.cancel(
            api_key=api_key,
            stripe_account=stripe_account,
        )

        # assert Order got cancelled
        assert cancelled_order["status"] == "canceled"

        # assert cancel called with the correct kwargs
        Order.stripe_class.cancel.assert_called_once_with(
            "order_fakefakefakefakefake0001",
            api_key=expected_api_key,
            stripe_account=stripe_account or FAKE_PLATFORM_ACCOUNT["id"],
        )

    @pytest.mark.parametrize("stripe_account", (None, "acct_fakefakefakefake001"))
    @pytest.mark.parametrize(
        "api_key, expected_api_key",
        (
            (None, djstripe_settings.STRIPE_SECRET_KEY),
            ("sk_fakefakefake01", "sk_fakefakefake01"),
        ),
    )
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
    @patch(
        "stripe.Order.reopen",
    )
    def test_reopen(
        self,
        order_reopen_mock,
        invoice_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        api_key,
        expected_api_key,
        stripe_account,
    ):
        fake_order = deepcopy(FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT)

        fake_order_reopen = deepcopy(FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT)
        fake_order_reopen["status"] = "open"
        order_reopen_mock.return_value = fake_order_reopen

        order = Order.sync_from_stripe_data(fake_order)
        assert order

        # Reopen the order
        reopened_order = order.reopen(
            api_key=api_key,
            stripe_account=stripe_account,
        )

        # assert Order got reopened
        assert reopened_order["status"] == "open"

        # assert reopen called with the correct kwargs
        Order.stripe_class.reopen.assert_called_once_with(
            "order_fakefakefakefakefake0001",
            api_key=expected_api_key,
            stripe_account=stripe_account or FAKE_PLATFORM_ACCOUNT["id"],
        )

    @pytest.mark.parametrize("stripe_account", (None, "acct_fakefakefakefake001"))
    @pytest.mark.parametrize(
        "api_key, expected_api_key",
        (
            (None, djstripe_settings.STRIPE_SECRET_KEY),
            ("sk_fakefakefake01", "sk_fakefakefake01"),
        ),
    )
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
    @patch(
        "stripe.Order.submit",
    )
    def test_submit(
        self,
        order_submit_mock,
        invoice_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        api_key,
        expected_api_key,
        stripe_account,
    ):
        fake_order = deepcopy(FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT)

        fake_order_submit = deepcopy(FAKE_ORDER_WITH_CUSTOMER_WITH_PAYMENT_INTENT)
        fake_order_submit["status"] = "submitted"
        order_submit_mock.return_value = fake_order_submit

        order = Order.sync_from_stripe_data(fake_order)
        assert order

        expected_total = fake_order["amount_total"]

        # Submit the order
        submitted_order = order.submit(
            api_key=api_key,
            stripe_account=stripe_account,
            expected_total=expected_total,
        )

        # assert Order got submitted
        assert submitted_order["status"] == "submitted"

        # assert submit called with the correct kwargs
        Order.stripe_class.submit.assert_called_once_with(
            "order_fakefakefakefakefake0001",
            api_key=expected_api_key,
            stripe_account=stripe_account or FAKE_PLATFORM_ACCOUNT["id"],
            expected_total=expected_total,
        )
