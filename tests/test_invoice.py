"""
dj-stripe Invoice Model Tests.
"""
from copy import deepcopy
from decimal import Decimal
from unittest.mock import call, patch

import pytest
import stripe
from django.contrib.auth import get_user_model
from django.test.testcases import TestCase
from stripe.error import InvalidRequestError

from djstripe.enums import InvoiceStatus
from djstripe.models import Invoice, Plan, Subscription, UpcomingInvoice
from djstripe.settings import djstripe_settings

from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_INVOICE,
    FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE,
    FAKE_INVOICEITEM,
    FAKE_LINE_ITEM_SUBSCRIPTION,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PLAN,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_ITEM,
    FAKE_TAX_RATE_EXAMPLE_1_VAT,
    FAKE_TAX_RATE_EXAMPLE_2_SALES,
    FAKE_UPCOMING_INVOICE,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


class InvoiceTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        # create a Stripe Platform Account
        self.account = FAKE_PLATFORM_ACCOUNT.create()

        user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(user)

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
            "djstripe.Invoice.default_payment_method",
            "djstripe.Invoice.default_source",
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
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
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
        "stripe.SubscriptionItem.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_ITEM),
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
        subscription_item_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
        customer_retrieve_mock,
    ):
        default_account_mock.return_value = self.account
        invoice = Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))
        assert invoice
        assert (
            str(invoice) == f"Invoice #{FAKE_INVOICE['number']} for $20.00 USD (paid)"
        )
        self.assertGreater(len(invoice.status_transitions.keys()), 1)
        self.assertTrue(bool(invoice.account_country))
        self.assertTrue(bool(invoice.account_name))
        self.assertTrue(bool(invoice.collection_method))

        self.assertEqual(invoice.default_tax_rates.count(), 1)
        self.assertEqual(
            invoice.default_tax_rates.first().id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )

        self.assertEqual(invoice.total_tax_amounts.count(), 1)

        first_tax_amount = invoice.total_tax_amounts.first()
        self.assertEqual(
            first_tax_amount.tax_rate.id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )
        self.assertEqual(
            first_tax_amount.inclusive, FAKE_TAX_RATE_EXAMPLE_1_VAT["inclusive"]
        )
        self.assertEqual(first_tax_amount.amount, 261)

        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", autospec=True, return_value=deepcopy(FAKE_INVOICE)
    )
    def test_sync_from_stripe_data_update_total_tax_amounts(
        self,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
        customer_retrieve_mock,
    ):
        default_account_mock.return_value = self.account
        invoice = Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        # as per basic sync test
        self.assertEqual(invoice.default_tax_rates.count(), 1)
        self.assertEqual(
            invoice.default_tax_rates.first().id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )

        self.assertEqual(invoice.total_tax_amounts.count(), 1)

        first_tax_amount = invoice.total_tax_amounts.first()
        self.assertEqual(
            first_tax_amount.tax_rate.id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )
        self.assertEqual(
            first_tax_amount.inclusive, FAKE_TAX_RATE_EXAMPLE_1_VAT["inclusive"]
        )
        self.assertEqual(first_tax_amount.amount, 261)
        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

        # Now update with a different tax rate
        # TODO - should update tax rate in invoice items etc as well,
        #  but here we're mainly testing that invoice.total_tax_rates is
        #  correctly updated
        fake_updated_invoice = deepcopy(FAKE_INVOICE)
        fake_tax_rate_2 = deepcopy(FAKE_TAX_RATE_EXAMPLE_2_SALES)

        new_tax_amount = int(
            fake_updated_invoice["total"] * fake_tax_rate_2["percentage"] / 100
        )

        fake_updated_invoice.update(
            {
                "default_tax_rates": [fake_tax_rate_2],
                "tax": new_tax_amount,
                "total": fake_updated_invoice["total"] + new_tax_amount,
                "total_tax_amounts": [
                    {
                        "amount": new_tax_amount,
                        "inclusive": False,
                        "tax_rate": fake_tax_rate_2["id"],
                    }
                ],
            }
        )

        invoice_updated = Invoice.sync_from_stripe_data(fake_updated_invoice)

        self.assertEqual(invoice_updated.default_tax_rates.count(), 1)
        self.assertEqual(
            invoice_updated.default_tax_rates.first().id, fake_tax_rate_2["id"]
        )

        self.assertEqual(invoice_updated.total_tax_amounts.count(), 1)

        first_tax_amount = invoice_updated.total_tax_amounts.first()
        self.assertEqual(first_tax_amount.tax_rate.id, fake_tax_rate_2["id"])
        self.assertEqual(first_tax_amount.inclusive, fake_tax_rate_2["inclusive"])
        self.assertEqual(first_tax_amount.amount, new_tax_amount)
        self.assert_fks(
            invoice_updated, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve",
        autospec=True,
    )
    def test_sync_from_stripe_data_default_payment_method(
        self,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
        customer_retrieve_mock,
    ):
        default_account_mock.return_value = self.account
        fake_invoice = deepcopy(FAKE_INVOICE)
        fake_invoice["default_payment_method"] = deepcopy(FAKE_CARD_AS_PAYMENT_METHOD)
        invoice_retrieve_mock.return_value = fake_invoice

        invoice = Invoice.sync_from_stripe_data(fake_invoice)

        self.assertEqual(
            invoice.default_payment_method.id, FAKE_CARD_AS_PAYMENT_METHOD["id"]
        )

        self.assert_fks(
            invoice,
            expected_blank_fks=self.default_expected_blank_fks
            - {"djstripe.Invoice.default_payment_method"},
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    def test_billing_reason_enum(
        self,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account
        fake_invoice = deepcopy(FAKE_INVOICE)

        for billing_reason in (
            "subscription_cycle",
            "subscription_create",
            "subscription_update",
            "subscription",
            "manual",
            "upcoming",
            "subscription_threshold",
        ):
            fake_invoice["billing_reason"] = billing_reason

            invoice = Invoice.sync_from_stripe_data(fake_invoice)
            self.assertEqual(invoice.billing_reason, billing_reason)

            # trigger model field validation (including enum value choices check)
            invoice.full_clean()

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    def test_invoice_status_enum(
        self,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account
        fake_invoice = deepcopy(FAKE_INVOICE)

        for status in (
            "draft",
            "open",
            "paid",
            "uncollectible",
            "void",
        ):
            fake_invoice["status"] = status

            invoice = Invoice.sync_from_stripe_data(fake_invoice)
            self.assertEqual(invoice.status, status)

            # trigger model field validation (including enum value choices check)
            invoice.full_clean()

    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch("stripe.Invoice.retrieve", autospec=True)
    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
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
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_retry_true(
        self,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
    ):
        default_account_mock.return_value = self.account

        fake_invoice = deepcopy(FAKE_INVOICE)
        fake_invoice.update({"paid": False, "status": "open"})
        fake_invoice.update({"auto_advance": True})
        invoice_retrieve_mock.return_value = fake_invoice

        invoice = Invoice.sync_from_stripe_data(fake_invoice)
        return_value = invoice.retry()

        invoice_retrieve_mock.assert_called_once_with(
            id=invoice.id,
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            expand=[],
            stripe_account=invoice.djstripe_owner_account.id,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
        )
        self.assertTrue(return_value)

        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch("stripe.Invoice.retrieve", autospec=True)
    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
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
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_retry_false(
        self,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
    ):
        default_account_mock.return_value = self.account

        fake_invoice = deepcopy(FAKE_INVOICE)
        invoice_retrieve_mock.return_value = fake_invoice

        invoice = Invoice.sync_from_stripe_data(fake_invoice)
        return_value = invoice.retry()

        self.assertFalse(invoice_retrieve_mock.called)
        self.assertFalse(return_value)

        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
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
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    def test_status_draft(
        self,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data.update({"paid": False, "status": "draft"})
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertEqual(InvoiceStatus.draft, invoice.status)

        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
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
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    def test_status_open(
        self,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data.update({"paid": False, "status": "open"})
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertEqual(InvoiceStatus.open, invoice.status)

        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
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
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    def test_status_paid(
        self,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoice = Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        self.assertEqual(InvoiceStatus.paid, invoice.status)

        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
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
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    def test_status_uncollectible(
        self,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data.update({"paid": False, "status": "uncollectible"})
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertEqual(InvoiceStatus.uncollectible, invoice.status)

        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
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
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    def test_status_void(
        self,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data.update({"paid": False, "status": "void"})
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertEqual(InvoiceStatus.void, invoice.status)

        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
    )
    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.Plan.retrieve",
        return_value=deepcopy(FAKE_PLAN),
        autospec=True,
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_ITEM),
        autospec=True,
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_SUBSCRIPTION),
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_sync_no_subscription(
        self,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        subscription_item_retrieve_mock,
        plan_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
        customer_retrieve_mock,
    ):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data.update({"subscription": None})
        invoice_data["lines"]["data"][0]["subscription"] = None

        invoice_retrieve_mock.return_value = invoice_data
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertEqual(None, invoice.subscription)

        self.assertEqual(FAKE_CHARGE["id"], invoice.charge.id)
        plan_retrieve_mock.assert_not_called()

        self.assert_fks(
            invoice,
            expected_blank_fks=self.default_expected_blank_fks
            | {"djstripe.Invoice.subscription"},
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
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
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    def test_invoice_with_subscription_invoice_items(
        self,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        items = invoice.invoiceitems.all()
        self.assertEqual(1, len(items))

        self.assertEqual(items[0].id, "ii_fakefakefakefakefake0001")
        self.assertIsNone(items[0].subscription)

        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
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
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_invoice_with_no_invoice_items(
        self,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"] = []
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNotNone(invoice.plan)  # retrieved from invoice item
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
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
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    def test_invoice_with_non_subscription_invoice_items(
        self,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"]["data"].append(deepcopy(FAKE_LINE_ITEM_SUBSCRIPTION))
        invoice_data["lines"]["total_count"] += 1
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNotNone(invoice)
        # assert only 1 line item of type="invoice_item"
        self.assertEqual(1, len(invoice.invoiceitems.all()))

        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
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
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    def test_invoice_plan_from_invoice_items(
        self,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNotNone(invoice.plan)  # retrieved from invoice item
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
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
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
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
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    def test_invoice_plan_from_subscription(
        self,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"]["data"][0]["plan"] = None

        invoice = Invoice.sync_from_stripe_data(invoice_data)
        self.assertIsNotNone(invoice.plan)  # retrieved from subscription
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

        self.assert_fks(invoice, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_ITEM),
        autospec=True,
    )
    @patch("stripe.Subscription.retrieve", autospec=True)
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
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        autospec=True,
    )
    def test_invoice_without_plan(
        self,
        invoice_item_retrieve_mock,
        product_retrieve_mock,
        charge_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"]["data"][0]["plan"] = None
        invoice_data["lines"]["data"][0]["subscription"] = None
        invoice_data["subscription"] = None

        fake_invoice_item = deepcopy(FAKE_INVOICEITEM)
        fake_invoice_item["subscription"] = None
        invoice_item_retrieve_mock.return_value = fake_invoice_item

        subscription_retrieve_mock.return_value = deepcopy(FAKE_SUBSCRIPTION)

        invoice = Invoice.sync_from_stripe_data(invoice_data)
        self.assertIsNone(invoice.plan)

        self.assert_fks(
            invoice,
            expected_blank_fks=self.default_expected_blank_fks
            | {"djstripe.Invoice.subscription"},
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
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", autospec=True, return_value=deepcopy(FAKE_INVOICE)
    )
    @patch(
        "stripe.Plan.retrieve",
        return_value=deepcopy(FAKE_PLAN),
        autospec=True,
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.upcoming",
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_upcoming_invoice(
        self,
        product_retrieve_mock,
        invoice_upcoming_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        plan_retrieve_mock,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):

        fake_upcoming_invoice_data = deepcopy(FAKE_UPCOMING_INVOICE)
        fake_upcoming_invoice_data["lines"]["data"][0][
            "subscription"
        ] = FAKE_SUBSCRIPTION["id"]
        invoice_upcoming_mock.return_value = fake_upcoming_invoice_data

        fake_subscription_item_data = deepcopy(FAKE_SUBSCRIPTION_ITEM)
        fake_subscription_item_data["plan"] = deepcopy(FAKE_PLAN)
        fake_subscription_item_data["subscription"] = deepcopy(FAKE_SUBSCRIPTION)["id"]
        subscription_item_retrieve_mock.return_value = fake_subscription_item_data

        invoice = UpcomingInvoice.upcoming()
        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.id)
        self.assertIsNone(invoice.save())
        self.assertEqual(invoice.get_stripe_dashboard_url(), "")

        invoice.id = "foo"
        self.assertIsNone(invoice.id)

        # one more because of creating the associated line item
        subscription_retrieve_mock.assert_has_calls(
            [
                call(
                    api_key=djstripe_settings.STRIPE_SECRET_KEY,
                    expand=[],
                    id=FAKE_SUBSCRIPTION["id"],
                    stripe_account=None,
                ),
                call(
                    api_key=djstripe_settings.STRIPE_SECRET_KEY,
                    expand=[],
                    id=FAKE_SUBSCRIPTION["id"],
                    stripe_account=None,
                ),
            ]
        )

        plan_retrieve_mock.assert_not_called()

        items = invoice.lineitems.all()
        self.assertEqual(1, len(items))
        self.assertEqual("il_fakefakefakefakefake0002", items[0].id)
        self.assertEqual(0, invoice.invoiceitems.count())

        # delete/update should do nothing
        self.assertEqual(invoice.lineitems.update(), 0)
        self.assertEqual(invoice.lineitems.delete(), 0)

        self.assertIsNotNone(invoice.plan)
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

        invoice._lineitems = []
        items = invoice.lineitems.all()
        self.assertEqual(0, len(items))
        self.assertIsNotNone(invoice.plan)

        self.assertEqual(invoice.default_tax_rates.count(), 1)
        self.assertEqual(
            invoice.default_tax_rates.first().id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )

        self.assertEqual(invoice.total_tax_amounts.count(), 1)

        first_tax_amount = invoice.total_tax_amounts.first()
        self.assertEqual(
            first_tax_amount.tax_rate.id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )
        self.assertEqual(
            first_tax_amount.inclusive, FAKE_TAX_RATE_EXAMPLE_1_VAT["inclusive"]
        )
        self.assertEqual(first_tax_amount.amount, 261)

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
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", autospec=True, return_value=deepcopy(FAKE_INVOICE)
    )
    @patch("stripe.Plan.retrieve", autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.upcoming",
        autospec=True,
    )
    def test_upcoming_invoice_with_subscription(
        self,
        invoice_upcoming_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):

        fake_upcoming_invoice_data = deepcopy(FAKE_UPCOMING_INVOICE)
        fake_upcoming_invoice_data["lines"]["data"][0][
            "subscription"
        ] = FAKE_SUBSCRIPTION["id"]
        invoice_upcoming_mock.return_value = fake_upcoming_invoice_data

        fake_subscription_item_data = deepcopy(FAKE_SUBSCRIPTION_ITEM)
        fake_subscription_item_data["plan"] = deepcopy(FAKE_PLAN)
        fake_subscription_item_data["subscription"] = deepcopy(FAKE_SUBSCRIPTION)["id"]
        subscription_item_retrieve_mock.return_value = fake_subscription_item_data

        invoice = Invoice.upcoming(
            subscription=Subscription(id=FAKE_SUBSCRIPTION["id"])
        )
        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.id)
        self.assertIsNone(invoice.save())

        # one more because of creating the associated line item
        subscription_retrieve_mock.assert_has_calls(
            [
                call(
                    api_key=djstripe_settings.STRIPE_SECRET_KEY,
                    expand=[],
                    id=FAKE_SUBSCRIPTION["id"],
                    stripe_account=None,
                ),
                call(
                    api_key=djstripe_settings.STRIPE_SECRET_KEY,
                    expand=[],
                    id=FAKE_SUBSCRIPTION["id"],
                    stripe_account=None,
                ),
            ]
        )

        plan_retrieve_mock.assert_not_called()

        self.assertIsNotNone(invoice.plan)
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

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
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch("stripe.Invoice.retrieve", autospec=True)
    @patch("stripe.Plan.retrieve", autospec=True)
    @patch(
        "stripe.SubscriptionItem.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Invoice.upcoming",
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_upcoming_invoice_with_subscription_plan(
        self,
        product_retrieve_mock,
        invoice_upcoming_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        plan_retrieve_mock,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
        customer_retrieve_mock,
    ):
        fake_upcoming_invoice_data = deepcopy(FAKE_UPCOMING_INVOICE)
        fake_upcoming_invoice_data[
            "subscription"
        ] = FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE["id"]
        invoice_upcoming_mock.return_value = fake_upcoming_invoice_data

        fake_invoice_data = deepcopy(FAKE_INVOICE)
        fake_invoice_data["subscription"] = FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE[
            "id"
        ]
        fake_invoice_data["lines"]["data"][0][
            "subscription"
        ] = FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE["id"]
        invoice_retrieve_mock.return_value = fake_invoice_data

        fake_subscription_item_data = deepcopy(FAKE_SUBSCRIPTION_ITEM)
        fake_subscription_item_data["plan"] = deepcopy(FAKE_PLAN)
        subscription_item_retrieve_mock.return_value = fake_subscription_item_data

        fake_subscription_data = deepcopy(FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE)
        fake_subscription_data["plan"] = deepcopy(FAKE_PLAN)
        subscription_retrieve_mock.return_value = fake_subscription_data

        invoice = Invoice.upcoming(subscription_plan=Plan(id=FAKE_PLAN["id"]))
        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.id)
        self.assertIsNone(invoice.save())

        subscription_retrieve_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            expand=[],
            id=FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE["id"],
            stripe_account=None,
        )
        plan_retrieve_mock.assert_not_called()

        self.assertIsNotNone(invoice.plan)
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

    @patch(
        "stripe.Invoice.upcoming",
        side_effect=InvalidRequestError("Nothing to invoice for customer", None),
    )
    def test_no_upcoming_invoices(self, invoice_upcoming_mock):
        invoice = Invoice.upcoming()
        self.assertIsNone(invoice)

    @patch(
        "stripe.Invoice.upcoming",
        side_effect=InvalidRequestError("Some other error", None),
    )
    def test_upcoming_invoice_error(self, invoice_upcoming_mock):
        with self.assertRaises(InvalidRequestError):
            Invoice.upcoming()


class TestInvoiceDecimal:
    @pytest.mark.parametrize(
        "inputted,expected",
        [
            (Decimal("1"), Decimal("1.00")),
            (Decimal("1.5234567"), Decimal("1.52")),
            (Decimal("0"), Decimal("0.00")),
            (Decimal("23.2345678"), Decimal("23.23")),
            ("1", Decimal("1.00")),
            ("1.5234567", Decimal("1.52")),
            ("0", Decimal("0.00")),
            ("23.2345678", Decimal("23.23")),
            (1, Decimal("1.00")),
            (1.5234567, Decimal("1.52")),
            (0, Decimal("0.00")),
            (23.2345678, Decimal("23.24")),
        ],
    )
    def test_decimal_tax_percent(self, inputted, expected, monkeypatch):  # noqa: C901
        fake_invoice = deepcopy(FAKE_INVOICE)
        fake_invoice["tax_percent"] = inputted

        def mock_invoice_get(*args, **kwargs):
            return fake_invoice

        def mock_invoice_item_get(*args, **kwargs):
            return FAKE_INVOICEITEM

        def mock_customer_get(*args, **kwargs):
            return FAKE_CUSTOMER

        def mock_charge_get(*args, **kwargs):
            return FAKE_CHARGE

        def mock_payment_method_get(*args, **kwargs):
            return FAKE_CARD_AS_PAYMENT_METHOD

        def mock_payment_intent_get(*args, **kwargs):
            return FAKE_PAYMENT_INTENT_I

        def mock_subscription_get(*args, **kwargs):
            return FAKE_SUBSCRIPTION

        def mock_subscriptionitem_get(*args, **kwargs):
            return FAKE_SUBSCRIPTION_ITEM

        def mock_balance_transaction_get(*args, **kwargs):
            return FAKE_BALANCE_TRANSACTION

        def mock_product_get(*args, **kwargs):
            return FAKE_PRODUCT

        # monkeypatch stripe retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Invoice, "retrieve", mock_invoice_get)
        monkeypatch.setattr(stripe.InvoiceItem, "retrieve", mock_invoice_item_get)
        monkeypatch.setattr(stripe.Customer, "retrieve", mock_customer_get)
        monkeypatch.setattr(
            stripe.BalanceTransaction, "retrieve", mock_balance_transaction_get
        )
        monkeypatch.setattr(stripe.Subscription, "retrieve", mock_subscription_get)
        monkeypatch.setattr(
            stripe.SubscriptionItem, "retrieve", mock_subscriptionitem_get
        )
        monkeypatch.setattr(stripe.Charge, "retrieve", mock_charge_get)
        monkeypatch.setattr(stripe.PaymentMethod, "retrieve", mock_payment_method_get)
        monkeypatch.setattr(stripe.PaymentIntent, "retrieve", mock_payment_intent_get)
        monkeypatch.setattr(stripe.Product, "retrieve", mock_product_get)

        invoice = Invoice.sync_from_stripe_data(fake_invoice)
        field_data = invoice.tax_percent

        assert isinstance(field_data, Decimal)
        assert field_data == expected
