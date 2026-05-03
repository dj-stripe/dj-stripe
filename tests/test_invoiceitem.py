"""
dj-stripe InvoiceItem Model Tests.
"""

from copy import deepcopy
from unittest.mock import patch

from django.test.testcases import TestCase

from djstripe.models import Invoice, InvoiceItem
from djstripe.models.payment_methods import Card

from . import (
    FAKE_CARD_II,
    FAKE_CHARGE_II,
    FAKE_CUSTOMER_II,
    FAKE_INVOICE,
    FAKE_INVOICE_II,
    FAKE_INVOICEITEM,
    FAKE_INVOICEITEM_III,
    FAKE_PAYMENT_INTENT_II,
    FAKE_PAYMENT_METHOD_II,
    FAKE_PLAN_II,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_PRICE_II,
    FAKE_SUBSCRIPTION_III,
    FAKE_TAX_RATE_EXAMPLE_1_VAT,
    AssertStripeFksMixin,
    mock_stripe_world,
)
from .conftest import CreateAccountMixin


class InvoiceItemTest(CreateAccountMixin, AssertStripeFksMixin, TestCase):
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
            "djstripe.Invoice.default_payment_method",
            "djstripe.Invoice.default_source",
            "djstripe.Invoice.payment_intent",
            "djstripe.PaymentIntent.invoice (related name)",
            "djstripe.PaymentIntent.on_behalf_of",
            "djstripe.PaymentIntent.payment_method",
            "djstripe.PaymentIntent.upcominginvoice (related name)",
            "djstripe.Product.default_price",
            "djstripe.Subscription.default_payment_method",
            "djstripe.Subscription.default_source",
            "djstripe.Subscription.pending_setup_intent",
            "djstripe.Subscription.schedule",
        }

    def _patch_default_account(self):
        """Make Account.get_default_account return self.account for sync paths."""
        return patch(
            "djstripe.models.Account.get_default_account",
            autospec=True,
            return_value=self.account,
        )

    def _world_for_invoice_ii(self):
        """Stripe-world preset for tests that swap in the *_II fixture set."""
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_II)
        fake_payment_intent["invoice"] = FAKE_INVOICE_II["id"]
        fake_subscription = deepcopy(FAKE_SUBSCRIPTION_III)
        fake_subscription["latest_invoice"] = FAKE_INVOICE_II["id"]
        return mock_stripe_world(
            Invoice=FAKE_INVOICE_II,
            InvoiceItem=FAKE_INVOICEITEM,
            Charge=FAKE_CHARGE_II,
            Customer=FAKE_CUSTOMER_II,
            PaymentMethod=FAKE_PAYMENT_METHOD_II,
            PaymentIntent=fake_payment_intent,
            Subscription=fake_subscription,
        )

    def test___str__(self):
        fake_card = deepcopy(FAKE_CARD_II)
        fake_card["customer"] = None
        # create Card for FAKE_CUSTOMER_III
        Card.sync_from_stripe_data(fake_card)

        with mock_stripe_world():
            # create invoice for latest_invoice in subscription to work.
            Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))
            invoiceitem = InvoiceItem.sync_from_stripe_data(deepcopy(FAKE_INVOICEITEM))

        self.assertEqual(
            invoiceitem.get_stripe_dashboard_url(),
            invoiceitem.invoice.get_stripe_dashboard_url(),
        )
        assert str(invoiceitem) == invoiceitem.description

    def test_sync_with_subscription(self):
        fake_card = deepcopy(FAKE_CARD_II)
        fake_card["customer"] = None
        # create Card for FAKE_CUSTOMER_II
        Card.sync_from_stripe_data(fake_card)

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        invoiceitem_data["subscription"] = FAKE_SUBSCRIPTION_III["id"]
        invoiceitem_data["invoice"] = FAKE_INVOICE_II["id"]

        with self._patch_default_account(), self._world_for_invoice_ii() as mocks:
            mocks["InvoiceItem"].return_value = invoiceitem_data
            invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

            expected_blank_fks = (
                self.default_expected_blank_fks
                | {"djstripe.InvoiceItem.plan", "djstripe.InvoiceItem.price"}
            ) - {
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.Invoice.payment_intent",
            }
            self.assert_fks(invoiceitem, expected_blank_fks=expected_blank_fks)

            # Coverage of sync of existing data
            invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)
            self.assert_fks(invoiceitem, expected_blank_fks=expected_blank_fks)

        mocks["Invoice"].assert_called_once()
        assert mocks["Invoice"].call_args.kwargs["id"] == FAKE_INVOICE_II["id"]
        assert mocks["Invoice"].call_args.kwargs["expand"] == [
            "discounts",
            "lines.data.discounts",
        ]

    def test_sync_expanded_invoice_with_subscription(self):
        fake_card = deepcopy(FAKE_CARD_II)
        fake_card["customer"] = None
        # create Card for FAKE_CUSTOMER_III
        Card.sync_from_stripe_data(fake_card)

        with self._patch_default_account(), self._world_for_invoice_ii():
            # create invoice
            Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE_II))

            invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
            # Expand the Invoice data inline
            invoiceitem_data["subscription"] = FAKE_SUBSCRIPTION_III["id"]
            invoiceitem_data["invoice"] = deepcopy(dict(FAKE_INVOICE_II))
            invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

            expected_blank_fks = (
                self.default_expected_blank_fks
                | {"djstripe.InvoiceItem.plan", "djstripe.InvoiceItem.price"}
            ) - {
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.Invoice.payment_intent",
            }
            self.assert_fks(invoiceitem, expected_blank_fks=expected_blank_fks)

            # Coverage of sync of existing data
            invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)
            self.assert_fks(invoiceitem, expected_blank_fks=expected_blank_fks)

    def test_sync_proration(self):
        fake_card = deepcopy(FAKE_CARD_II)
        fake_card["customer"] = None
        # create Card for FAKE_CUSTOMER_III
        Card.sync_from_stripe_data(fake_card)

        # Like _world_for_invoice_ii but also swaps Plan/Price for the *_II
        # fixtures used by the proration item.
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_II)
        fake_payment_intent["invoice"] = FAKE_INVOICE_II["id"]
        fake_subscription = deepcopy(FAKE_SUBSCRIPTION_III)
        fake_subscription["latest_invoice"] = FAKE_INVOICE_II["id"]

        with (
            self._patch_default_account(),
            mock_stripe_world(
                Invoice=FAKE_INVOICE_II,
                InvoiceItem=FAKE_INVOICEITEM,
                Charge=FAKE_CHARGE_II,
                Customer=FAKE_CUSTOMER_II,
                PaymentMethod=FAKE_PAYMENT_METHOD_II,
                PaymentIntent=fake_payment_intent,
                Subscription=fake_subscription,
                Plan=FAKE_PLAN_II,
                Price=FAKE_PRICE_II,
            ),
        ):
            # create invoice
            Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE_II))

            invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
            invoiceitem_data.update(
                {
                    "proration": True,
                    "plan": FAKE_PLAN_II["id"],
                    "price": FAKE_PRICE_II["id"],
                }
            )
            invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        self.assertEqual(FAKE_PLAN_II["id"], invoiceitem.plan.id)
        self.assertEqual(FAKE_PRICE_II["id"], invoiceitem.price.id)

        expected_blank_fks = (
            self.default_expected_blank_fks | {"djstripe.InvoiceItem.subscription"}
        ) - {
            "djstripe.PaymentIntent.invoice (related name)",
            "djstripe.Invoice.payment_intent",
        }
        self.assert_fks(invoiceitem, expected_blank_fks=expected_blank_fks)

    def test_sync_null_invoice(self):
        with (
            self._patch_default_account(),
            mock_stripe_world(
                Charge=FAKE_CHARGE_II,
                Customer=FAKE_CUSTOMER_II,
                Subscription=FAKE_SUBSCRIPTION_III,
                Plan=FAKE_PLAN_II,
                Price=FAKE_PRICE_II,
            ),
        ):
            invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
            invoiceitem_data.update(
                {
                    "proration": True,
                    "plan": FAKE_PLAN_II["id"],
                    "price": FAKE_PRICE_II["id"],
                    "invoice": None,
                }
            )
            invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        self.assertEqual(FAKE_PLAN_II["id"], invoiceitem.plan.id)
        self.assertEqual(FAKE_PRICE_II["id"], invoiceitem.price.id)
        self.assert_fks(
            invoiceitem,
            expected_blank_fks=self.default_expected_blank_fks
            | {
                "djstripe.InvoiceItem.invoice",
                "djstripe.InvoiceItem.subscription",
                "djstripe.Customer.default_source",
            },
        )

    def test_sync_with_taxes(self):
        fake_card = deepcopy(FAKE_CARD_II)
        fake_card["customer"] = None
        # create Card for FAKE_CUSTOMER_III
        Card.sync_from_stripe_data(fake_card)

        with self._patch_default_account(), self._world_for_invoice_ii():
            # create invoice
            Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE_II))

            invoiceitem_data = deepcopy(FAKE_INVOICEITEM_III)
            invoiceitem_data["plan"] = FAKE_PLAN_II
            invoiceitem_data["price"] = FAKE_PRICE_II
            invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        self.assertEqual(invoiceitem.tax_rates.count(), 1)
        self.assertEqual(
            invoiceitem.tax_rates.first().id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )
