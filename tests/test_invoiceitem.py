"""
dj-stripe InvoiceItem Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.test.testcases import TestCase

from djstripe.models import InvoiceItem
from djstripe.settings import STRIPE_SECRET_KEY

from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_CHARGE_II,
    FAKE_CUSTOMER_II,
    FAKE_INVOICE_II,
    FAKE_INVOICEITEM,
    FAKE_INVOICEITEM_III,
    FAKE_PLAN_II,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION_III,
    FAKE_TAX_RATE_EXAMPLE_1_VAT,
    IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    AssertStripeFksMixin,
    default_account,
)


class InvoiceItemTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        self.account = default_account()

        self.default_expected_blank_fks = {
            "djstripe.Account.branding_logo",
            "djstripe.Account.branding_icon",
            "djstripe.Charge.dispute",
            "djstripe.Charge.latest_upcominginvoice (related name)",
            "djstripe.Charge.payment_intent",
            "djstripe.Charge.payment_method",
            "djstripe.Charge.transfer",
            "djstripe.Customer.coupon",
            "djstripe.Customer.default_payment_method",
            "djstripe.Customer.subscriber",
            "djstripe.Invoice.default_payment_method",
            "djstripe.Invoice.default_source",
            "djstripe.Invoice.payment_intent",
            "djstripe.Subscription.default_payment_method",
            "djstripe.Subscription.default_source",
            "djstripe.Subscription.pending_setup_intent",
        }

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_III),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II), autospec=True
    )
    def test_str(
        self,
        invoice_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        product_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        invoiceitem_data["plan"] = FAKE_PLAN_II
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)
        self.assertEqual(
            invoiceitem.get_stripe_dashboard_url(),
            invoiceitem.invoice.get_stripe_dashboard_url(),
        )

        self.assertEqual(str(invoiceitem), FAKE_PRODUCT["name"])
        invoiceitem.plan = None
        self.assertEqual(
            str(invoiceitem),
            "<amount=20, date=2015-08-08 11:26:56+00:00, "
            "id=ii_16XVTY2eZvKYlo2Cxz5n3RaS>",
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_III),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II), autospec=True
    )
    def test_sync_with_subscription(
        self,
        invoice_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        product_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        invoiceitem_data.update({"subscription": FAKE_SUBSCRIPTION_III["id"]})
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        expected_blank_fks = self.default_expected_blank_fks | {
            "djstripe.InvoiceItem.plan"
        }

        self.assert_fks(invoiceitem, expected_blank_fks=expected_blank_fks)

        # Coverage of sync of existing data
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        self.assert_fks(invoiceitem, expected_blank_fks=expected_blank_fks)

        invoice_retrieve_mock.assert_called_once_with(
            api_key=STRIPE_SECRET_KEY,
            expand=[],
            id=FAKE_INVOICE_II["id"],
            stripe_account=None,
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_III),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II), autospec=True
    )
    @patch("stripe.Invoice.retrieve", autospec=True)
    def test_sync_expanded_invoice_with_subscription(
        self,
        invoice_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        product_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        # Expand the Invoice data
        invoiceitem_data.update(
            {
                "subscription": FAKE_SUBSCRIPTION_III["id"],
                "invoice": deepcopy(dict(FAKE_INVOICE_II)),
            }
        )
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        expected_blank_fks = self.default_expected_blank_fks | {
            "djstripe.InvoiceItem.plan"
        }

        self.assert_fks(invoiceitem, expected_blank_fks=expected_blank_fks)

        # Coverage of sync of existing data
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        self.assert_fks(invoiceitem, expected_blank_fks=expected_blank_fks)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN_II), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_III),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II), autospec=True
    )
    def test_sync_proration(
        self,
        invoice_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        invoiceitem_data.update({"proration": True, "plan": FAKE_PLAN_II["id"]})
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        self.assertEqual(FAKE_PLAN_II["id"], invoiceitem.plan.id)

        self.assert_fks(
            invoiceitem,
            expected_blank_fks=self.default_expected_blank_fks
            | {"djstripe.InvoiceItem.subscription"},
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN_II), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_III),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II), autospec=True
    )
    @patch("stripe.Invoice.retrieve", autospec=True)
    def test_sync_null_invoice(
        self,
        invoice_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        invoiceitem_data.update(
            {"proration": True, "plan": FAKE_PLAN_II["id"], "invoice": None}
        )
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        self.assertEqual(FAKE_PLAN_II["id"], invoiceitem.plan.id)

        self.assert_fks(
            invoiceitem,
            expected_blank_fks=self.default_expected_blank_fks
            | {"djstripe.InvoiceItem.invoice", "djstripe.InvoiceItem.subscription"},
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_III),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE_II), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II), autospec=True
    )
    def test_sync_with_taxes(
        self,
        invoice_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        product_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM_III)
        invoiceitem_data["plan"] = FAKE_PLAN_II
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        self.assertEqual(invoiceitem.tax_rates.count(), 1)
        self.assertEqual(
            invoiceitem.tax_rates.first().id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )
