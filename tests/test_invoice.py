"""
dj-stripe Invoice Model Tests.
"""

from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test.testcases import TestCase
from stripe import InvalidRequestError

from djstripe.models import Invoice, Plan, Subscription, UpcomingInvoice

from . import (
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CUSTOMER,
    FAKE_INVOICE,
    FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE,
    FAKE_INVOICEITEM,
    FAKE_LINE_ITEM_SUBSCRIPTION,
    FAKE_PLAN,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_ITEM,
    FAKE_TAX_RATE_EXAMPLE_1_VAT,
    FAKE_UPCOMING_INVOICE,
    AssertStripeFksMixin,
    mock_stripe_world,
    monkeypatch_stripe_world,
)
from .conftest import CreateAccountMixin

pytestmark = pytest.mark.django_db


class InvoiceTest(CreateAccountMixin, AssertStripeFksMixin, TestCase):
    def setUp(self):
        # create a Stripe Platform Account
        self.account = FAKE_PLATFORM_ACCOUNT.create()

        user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(user)

    def _patch_default_account(self):
        """Make Account.get_default_account return self.account for sync paths."""
        return patch(
            "djstripe.models.Account.get_default_account",
            autospec=True,
            return_value=self.account,
        )

    def test_sync_from_stripe_data(self):
        with self._patch_default_account(), mock_stripe_world():
            invoice = Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        assert invoice
        # Invoice.__str__ formats amount_paid (in cents) as a raw value.
        assert str(invoice) == (
            f"Invoice #{FAKE_INVOICE['number']} for $2,000.00 USD (paid)"
        )
        self.assertGreater(len(invoice.status_transitions.keys()), 1)
        self.assertTrue(bool(invoice.account_country))
        self.assertTrue(bool(invoice.account_name))
        self.assertTrue(bool(invoice.collection_method))

        self.assertEqual(invoice.default_tax_rates.count(), 1)
        self.assertEqual(
            invoice.default_tax_rates.first().id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )
        self.assert_fks(invoice)

    def test_sync_from_stripe_data_default_payment_method(self):
        fake_invoice = deepcopy(FAKE_INVOICE)
        fake_invoice["default_payment_method"] = deepcopy(FAKE_CARD_AS_PAYMENT_METHOD)

        with (
            self._patch_default_account(),
            mock_stripe_world(Invoice=fake_invoice),
        ):
            invoice = Invoice.sync_from_stripe_data(fake_invoice)

        self.assertEqual(
            invoice.default_payment_method.id, FAKE_CARD_AS_PAYMENT_METHOD["id"]
        )
        self.assert_fks(invoice)

    def test_billing_reason_enum(self):
        with self._patch_default_account(), mock_stripe_world():
            for billing_reason in (
                "subscription_cycle",
                "subscription_create",
                "subscription_update",
                "subscription",
                "manual",
                "upcoming",
                "subscription_threshold",
            ):
                with self.subTest(billing_reason=billing_reason):
                    fake_invoice = deepcopy(FAKE_INVOICE)
                    fake_invoice["billing_reason"] = billing_reason
                    invoice = Invoice.sync_from_stripe_data(fake_invoice)
                    self.assertEqual(invoice.billing_reason, billing_reason)
                    # trigger model field validation (including enum value choices check)
                    invoice.full_clean()

    def test_invoice_status_enum(self):
        with self._patch_default_account(), mock_stripe_world():
            for status in ("draft", "open", "paid", "uncollectible", "void"):
                with self.subTest(status=status):
                    fake_invoice = deepcopy(FAKE_INVOICE)
                    fake_invoice["status"] = status
                    invoice = Invoice.sync_from_stripe_data(fake_invoice)
                    self.assertEqual(invoice.status, status)
                    invoice.full_clean()

    def test_retry_true(self):
        fake_invoice = deepcopy(FAKE_INVOICE)
        fake_invoice.update({"paid": False, "status": "open", "auto_advance": True})

        with (
            self._patch_default_account(),
            mock_stripe_world(Invoice=fake_invoice) as mocks,
        ):
            invoice = Invoice.sync_from_stripe_data(fake_invoice)
            return_value = invoice.retry()

        mocks["Invoice"].assert_called_once()
        assert mocks["Invoice"].call_args.kwargs["id"] == invoice.id
        assert mocks["Invoice"].call_args.kwargs["expand"] == [
            "discounts",
            "lines.data.discounts",
        ]
        self.assertTrue(return_value)
        self.assert_fks(invoice)

    def test_retry_false(self):
        # FAKE_INVOICE is paid, so retry() short-circuits before calling
        # stripe.Invoice.retrieve a second time.
        with self._patch_default_account(), mock_stripe_world() as mocks:
            invoice = Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))
            return_value = invoice.retry()

        self.assertFalse(mocks["Invoice"].called)
        self.assertFalse(return_value)
        self.assert_fks(invoice)

    def test_sync_no_subscription(self):
        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["subscription"] = None
        invoice_data["lines"]["data"][0]["subscription"] = None

        with (
            self._patch_default_account(),
            mock_stripe_world(Invoice=invoice_data) as mocks,
        ):
            invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNone(invoice.subscription)
        self.assertEqual(FAKE_SUBSCRIPTION["latest_invoice"], invoice.id)
        mocks["Plan"].assert_not_called()
        self.assert_fks(invoice, expected_blank_fks={"djstripe.Invoice.subscription"})

    def test_invoice_with_subscription_invoice_items(self):
        with self._patch_default_account(), mock_stripe_world():
            invoice = Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        items = invoice.invoiceitems.all()
        self.assertEqual(1, len(items))
        self.assertEqual(items[0].id, "ii_fakefakefakefakefake0001")
        self.assertIsNone(items[0].subscription)
        self.assert_fks(invoice)

    def test_invoice_with_no_invoice_items(self):
        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"] = []

        with self._patch_default_account(), mock_stripe_world():
            invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNotNone(invoice.plan)  # retrieved from invoice item
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)
        self.assert_fks(invoice)

    def test_invoice_with_non_subscription_invoice_items(self):
        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"]["data"].append(deepcopy(FAKE_LINE_ITEM_SUBSCRIPTION))
        invoice_data["lines"]["total_count"] += 1

        with self._patch_default_account(), mock_stripe_world():
            invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNotNone(invoice)
        # only 1 line item of type="invoice_item"
        self.assertEqual(1, len(invoice.invoiceitems.all()))
        self.assert_fks(invoice)

    def test_invoice_plan_from_invoice_items(self):
        with self._patch_default_account(), mock_stripe_world():
            invoice = Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        self.assertIsNotNone(invoice.plan)  # retrieved from invoice item
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)
        self.assert_fks(invoice)

    def test_invoice_plan_from_subscription(self):
        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"]["data"][0]["plan"] = None

        with self._patch_default_account(), mock_stripe_world():
            invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNotNone(invoice.plan)  # retrieved from subscription
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)
        self.assert_fks(invoice)

    def test_invoice_without_plan(self):
        invoice_data = deepcopy(FAKE_INVOICE)
        invoice_data["lines"]["data"][0]["plan"] = None
        invoice_data["lines"]["data"][0]["subscription"] = None
        invoice_data["subscription"] = None

        fake_invoice_item = deepcopy(FAKE_INVOICEITEM)
        fake_invoice_item["subscription"] = None

        with (
            self._patch_default_account(),
            mock_stripe_world(InvoiceItem=fake_invoice_item),
        ):
            invoice = Invoice.sync_from_stripe_data(invoice_data)

        self.assertIsNone(invoice.plan)
        self.assert_fks(invoice, expected_blank_fks={"djstripe.Invoice.subscription"})

    def test_upcoming_invoice(self):
        fake_upcoming_invoice_data = deepcopy(FAKE_UPCOMING_INVOICE)
        fake_upcoming_invoice_data["lines"]["data"][0]["subscription"] = (
            FAKE_SUBSCRIPTION["id"]
        )

        fake_subscription_item_data = deepcopy(FAKE_SUBSCRIPTION_ITEM)
        fake_subscription_item_data["plan"] = deepcopy(FAKE_PLAN)
        fake_subscription_item_data["subscription"] = FAKE_SUBSCRIPTION["id"]

        with (
            patch(
                "stripe.Invoice.upcoming",
                return_value=fake_upcoming_invoice_data,
                autospec=True,
            ),
            mock_stripe_world(SubscriptionItem=fake_subscription_item_data) as mocks,
        ):
            invoice = UpcomingInvoice.upcoming()

        assert invoice
        self.assertIsNone(invoice.id)
        self.assertIsNone(invoice.save())
        self.assertEqual(invoice.get_stripe_dashboard_url(), "")

        invoice.id = "foo"
        self.assertIsNone(invoice.id)

        # one more because of creating the associated line item
        assert mocks["Subscription"].call_count == 2
        for kwargs in (c.kwargs for c in mocks["Subscription"].call_args_list):
            assert kwargs["id"] == FAKE_SUBSCRIPTION["id"]
        mocks["Plan"].assert_not_called()

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

    def test_upcoming_invoice_with_subscription(self):
        fake_upcoming_invoice_data = deepcopy(FAKE_UPCOMING_INVOICE)
        fake_upcoming_invoice_data["lines"]["data"][0]["subscription"] = (
            FAKE_SUBSCRIPTION["id"]
        )

        fake_subscription_item_data = deepcopy(FAKE_SUBSCRIPTION_ITEM)
        fake_subscription_item_data["plan"] = deepcopy(FAKE_PLAN)
        fake_subscription_item_data["subscription"] = FAKE_SUBSCRIPTION["id"]

        with (
            patch(
                "stripe.Invoice.upcoming",
                return_value=fake_upcoming_invoice_data,
                autospec=True,
            ),
            mock_stripe_world(SubscriptionItem=fake_subscription_item_data) as mocks,
        ):
            invoice = Invoice.upcoming(
                subscription=Subscription(id=FAKE_SUBSCRIPTION["id"])
            )

        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.id)
        self.assertIsNone(invoice.save())

        # one more because of creating the associated line item
        assert mocks["Subscription"].call_count == 2
        for kwargs in (c.kwargs for c in mocks["Subscription"].call_args_list):
            assert kwargs["id"] == FAKE_SUBSCRIPTION["id"]
        mocks["Plan"].assert_not_called()

        self.assertIsNotNone(invoice.plan)
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

    def test_upcoming_invoice_with_subscription_plan(self):
        fake_upcoming_invoice_data = deepcopy(FAKE_UPCOMING_INVOICE)
        fake_upcoming_invoice_data["subscription"] = (
            FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE["id"]
        )

        fake_invoice_data = deepcopy(FAKE_INVOICE)
        fake_invoice_data["subscription"] = FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE["id"]
        fake_invoice_data["lines"]["data"][0]["subscription"] = (
            FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE["id"]
        )
        fake_invoice_data["lines"]["data"][0]["discounts"][0]["subscription"] = (
            FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE["id"]
        )

        fake_subscription_item_data = deepcopy(FAKE_SUBSCRIPTION_ITEM)
        fake_subscription_item_data["plan"] = deepcopy(FAKE_PLAN)

        fake_subscription_data = deepcopy(FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE)
        fake_subscription_data["plan"] = deepcopy(FAKE_PLAN)

        with (
            patch(
                "stripe.Invoice.upcoming",
                return_value=fake_upcoming_invoice_data,
                autospec=True,
            ),
            mock_stripe_world(
                Invoice=fake_invoice_data,
                SubscriptionItem=fake_subscription_item_data,
                Subscription=fake_subscription_data,
            ) as mocks,
        ):
            invoice = Invoice.upcoming(subscription_plan=Plan(id=FAKE_PLAN["id"]))

        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.id)
        self.assertIsNone(invoice.save())

        mocks["Subscription"].assert_called_once()
        assert (
            mocks["Subscription"].call_args.kwargs["id"]
            == FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE["id"]
        )
        mocks["Plan"].assert_not_called()

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


class TestInvoiceDecimal(CreateAccountMixin):
    @pytest.mark.parametrize(
        "inputted,expected",
        [
            (Decimal(1), Decimal("1.00")),
            (Decimal("1.5234567"), Decimal("1.52")),
            (Decimal(0), Decimal("0.00")),
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
    def test_decimal_tax_percent(self, inputted, expected, monkeypatch):
        fake_invoice = deepcopy(FAKE_INVOICE)
        fake_invoice["tax_percent"] = inputted

        monkeypatch_stripe_world(monkeypatch, Invoice=fake_invoice)

        invoice = Invoice.sync_from_stripe_data(fake_invoice)
        field_data = invoice.tax_percent

        assert isinstance(field_data, Decimal)
        assert field_data == expected
