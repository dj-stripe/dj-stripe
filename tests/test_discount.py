"""
dj-stripe Discount model tests
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.test.testcases import TestCase

from djstripe.models.billing import Discount

from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_DISCOUNT,
    FAKE_DISCOUNT_CUSTOMER,
    FAKE_INVOICE,
    FAKE_INVOICEITEM,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_ITEM,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


class TestDiscount(AssertStripeFksMixin, TestCase):
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
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
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
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
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", autospec=True, return_value=deepcopy(FAKE_INVOICE)
    )
    def test_sync_from_stripe_data(
        self,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_discount_data = deepcopy(FAKE_DISCOUNT)

        discount = Discount.sync_from_stripe_data(fake_discount_data)

        self.assertEqual(discount.id, fake_discount_data["id"])
        self.assertEqual(discount.customer.id, fake_discount_data["customer"]["id"])
        self.assertEqual(discount.subscription.id, fake_discount_data["subscription"])
        self.assert_fks(
            discount,
            expected_blank_fks={
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
                "djstripe.Customer.coupon",
                "djstripe.Customer.discount",
                "djstripe.Charge.application_fee",
                "djstripe.Charge.dispute",
                "djstripe.Charge.latest_upcominginvoice (related name)",
                "djstripe.Charge.on_behalf_of",
                "djstripe.Charge.source_transfer",
                "djstripe.Charge.transfer",
                "djstripe.Discount.checkout_session",
                "djstripe.Discount.invoice",
                "djstripe.Discount.invoice_item",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.PaymentIntent.upcominginvoice (related name)",
                "djstripe.Product.default_price",
                "djstripe.Invoice.default_payment_method",
                "djstripe.Invoice.default_source",
                "djstripe.Invoice.subscription",
                "djstripe.Subscription.default_payment_method",
                "djstripe.Subscription.default_source",
                "djstripe.Subscription.pending_setup_intent",
                "djstripe.Subscription.schedule",
            },
        )

    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
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
        "stripe.Customer.retrieve",
        autospec=True,
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
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", autospec=True, return_value=deepcopy(FAKE_INVOICE)
    )
    def test__attach_objects_post_save_hook(
        self,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_customer_with_discount = deepcopy(FAKE_CUSTOMER)
        fake_customer_with_discount["discount"] = FAKE_DISCOUNT_CUSTOMER
        customer_retrieve_mock.return_value = fake_customer_with_discount

        fake_discount_data = deepcopy(FAKE_DISCOUNT_CUSTOMER)
        discount = Discount.sync_from_stripe_data(fake_discount_data)

        self.assertEqual(discount.id, fake_discount_data["id"])

        # Assert Customer.discount is populated
        discount.customer.refresh_from_db()
        self.assertIsNotNone(discount.customer.discount)
        self.assertEqual(discount.customer.discount, fake_discount_data)
