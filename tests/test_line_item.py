"""
dj-stripe LineItem Model Tests.
"""

import uuid
from copy import deepcopy
from unittest.mock import patch

import pytest
import stripe
from django.conf import settings
from django.test.testcases import TestCase

from djstripe.models import Invoice
from djstripe.models.billing import LineItem
from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_INVOICE,
    FAKE_INVOICEITEM,
    FAKE_LINE_ITEM,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_ITEM,
    AssertStripeFksMixin,
)


class LineItemTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        # create a Stripe Platform Account
        self.account = FAKE_PLATFORM_ACCOUNT.create()

        self.default_expected_blank_fks = {
            "djstripe.Account.branding_logo",
            "djstripe.Account.branding_icon",
            "djstripe.Charge.application_fee",
            "djstripe.Charge.dispute",
            "djstripe.Charge.latest_upcominginvoice (related name)",
            "djstripe.Charge.on_behalf_of",
            "djstripe.Charge.source_transfer",
            "djstripe.Charge.transfer",
            "djstripe.Customer.coupon",
            "djstripe.Customer.default_payment_method",
            "djstripe.Customer.subscriber",
            "djstripe.Customer.coupon",
            "djstripe.Invoice.default_payment_method",
            "djstripe.Invoice.default_source",
            "djstripe.InvoiceItem.plan",
            "djstripe.InvoiceItem.price",
            "djstripe.InvoiceItem.subscription",
            "djstripe.PaymentIntent.on_behalf_of",
            "djstripe.PaymentIntent.payment_method",
            "djstripe.PaymentIntent.upcominginvoice (related name)",
            "djstripe.Product.default_price",
            "djstripe.Subscription.default_payment_method",
            "djstripe.Subscription.default_source",
            "djstripe.Subscription.pending_setup_intent",
            "djstripe.Subscription.schedule",
        }

    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
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
        autospec=True,
        return_value=deepcopy(FAKE_SUBSCRIPTION),
    )
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
        "stripe.Customer.retrieve", autospec=True, return_value=deepcopy(FAKE_CUSTOMER)
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_CHARGE),
        autospec=True,
    )
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
    def test_sync_from_stripe_data(
        self,
        invoice_retrieve_mock,
        invoiceitem_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        paymentintent_retrieve_mock,
        paymentmethod_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        product_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        # create the latest invoice as Line Items (Invoice) need to exist on an Invoice
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        # Create the Line Item
        il = LineItem.sync_from_stripe_data(deepcopy(FAKE_LINE_ITEM))

        self.assertEqual(il.id, "il_fakefakefakefakefake0001")

        self.assert_fks(
            il,
            expected_blank_fks=(self.default_expected_blank_fks),
        )

    @pytest.mark.stripe_api
    @pytest.mark.usefixtures("configure_settings")
    def test_api_list(self):
        stripe_customer = stripe.Customer.create(
            api_key=settings.STRIPE_SECRET_KEY,
            email=f"line-item-api-list-{uuid.uuid4().hex}@example.com",
            metadata={"djstripe_test": "line_item_api_list"},
        )
        product = stripe.Product.create(
            api_key=settings.STRIPE_SECRET_KEY,
            name=f"djstripe-line-item-product-{uuid.uuid4().hex}",
        )
        price = stripe.Price.create(
            api_key=settings.STRIPE_SECRET_KEY,
            product=product.id,
            unit_amount=100,
            currency="usd",
        )
        invoice = None
        try:
            invoice_item = stripe.InvoiceItem.create(
                api_key=settings.STRIPE_SECRET_KEY,
                customer=stripe_customer.id,
                price=price.id,
                quantity=1,
            )
            invoice = stripe.Invoice.create(
                api_key=settings.STRIPE_SECRET_KEY,
                customer=stripe_customer.id,
                auto_advance=False,
            )

            line_items = list(
                LineItem.api_list(
                    id=invoice.id, api_key=settings.STRIPE_SECRET_KEY, limit=100
                )
            )
            self.assertTrue(
                any(item.invoice_item == invoice_item.id for item in line_items)
            )
        finally:
            if invoice is not None:
                stripe.Invoice.delete(invoice.id, api_key=settings.STRIPE_SECRET_KEY)
            stripe.Price.modify(
                price.id, api_key=settings.STRIPE_SECRET_KEY, active=False
            )
            stripe.Product.delete(product.id, api_key=settings.STRIPE_SECRET_KEY)
            stripe.Customer.delete(
                stripe_customer.id, api_key=settings.STRIPE_SECRET_KEY
            )
