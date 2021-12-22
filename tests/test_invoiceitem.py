"""
dj-stripe InvoiceItem Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.test.testcases import TestCase

from djstripe.models import Invoice, InvoiceItem
from djstripe.models.payment_methods import Card
from djstripe.settings import djstripe_settings

from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CARD_II,
    FAKE_CHARGE,
    FAKE_CHARGE_II,
    FAKE_CUSTOMER,
    FAKE_CUSTOMER_II,
    FAKE_INVOICE,
    FAKE_INVOICE_II,
    FAKE_INVOICEITEM,
    FAKE_INVOICEITEM_III,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PAYMENT_INTENT_II,
    FAKE_PAYMENT_METHOD_II,
    FAKE_PLAN,
    FAKE_PLAN_II,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_PRICE_II,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_III,
    FAKE_TAX_RATE_EXAMPLE_1_VAT,
    IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    AssertStripeFksMixin,
)


class InvoiceItemTest(AssertStripeFksMixin, TestCase):
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
            "djstripe.Subscription.default_payment_method",
            "djstripe.Subscription.default_source",
            "djstripe.Subscription.pending_setup_intent",
            "djstripe.Subscription.schedule",
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
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        side_effect=[
            deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
            deepcopy(FAKE_PAYMENT_METHOD_II),
        ],
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        side_effect=[deepcopy(FAKE_PAYMENT_INTENT_I), deepcopy(FAKE_PAYMENT_INTENT_II)],
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        side_effect=[deepcopy(FAKE_CHARGE), deepcopy(FAKE_CHARGE_II)],
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve",
        side_effect=[deepcopy(FAKE_INVOICE), deepcopy(FAKE_INVOICE_II)],
        autospec=True,
    )
    def test___str__(
        self,
        invoice_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        paymentintent_retrieve_mock,
        paymentmethod_retrieve_mock,
        subscription_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION_III)
        fake_subscription["latest_invoice"] = FAKE_INVOICE["id"]
        subscription_retrieve_mock.side_effect = [
            deepcopy(FAKE_SUBSCRIPTION),
            fake_subscription,
        ]

        fake_customer = deepcopy(FAKE_CUSTOMER_II)
        customer_retrieve_mock.side_effect = [deepcopy(FAKE_CUSTOMER), fake_customer]

        fake_card = deepcopy(FAKE_CARD_II)
        fake_card["customer"] = None
        # create Card for FAKE_CUSTOMER_III
        Card.sync_from_stripe_data(fake_card)

        # create invoice for latest_invoice in subscription to work.
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        # create invoice
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE_II))

        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        invoiceitem_data["plan"] = FAKE_PLAN_II
        invoiceitem_data["price"] = FAKE_PRICE_II
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)
        self.assertEqual(
            invoiceitem.get_stripe_dashboard_url(),
            invoiceitem.invoice.get_stripe_dashboard_url(),
        )

        assert str(invoiceitem) == invoiceitem.description

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
        autospec=True,
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_II),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        return_value=deepcopy(FAKE_CHARGE_II),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve",
        return_value=deepcopy(FAKE_INVOICE_II),
        autospec=True,
    )
    def test_sync_with_subscription(
        self,
        invoice_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        paymentintent_retrieve_mock,
        paymentmethod_retrieve_mock,
        subscription_retrieve_mock,
        product_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_II)
        fake_payment_intent["invoice"] = FAKE_INVOICE_II["id"]
        paymentintent_retrieve_mock.return_value = fake_payment_intent

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION_III)
        fake_subscription["latest_invoice"] = FAKE_INVOICE_II["id"]
        subscription_retrieve_mock.return_value = fake_subscription

        fake_customer = deepcopy(FAKE_CUSTOMER_II)
        customer_retrieve_mock.return_value = fake_customer

        fake_card = deepcopy(FAKE_CARD_II)
        fake_card["customer"] = None

        # create Card for FAKE_CUSTOMER_III
        Card.sync_from_stripe_data(fake_card)

        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM)
        invoiceitem_data.update({"subscription": fake_subscription["id"]})
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        expected_blank_fks = self.default_expected_blank_fks | {
            "djstripe.InvoiceItem.plan",
            "djstripe.InvoiceItem.price",
        }
        expected_blank_fks.difference_update(
            {
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.Invoice.payment_intent",
            }
        )

        self.assert_fks(invoiceitem, expected_blank_fks=expected_blank_fks)

        # Coverage of sync of existing data
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        self.assert_fks(invoiceitem, expected_blank_fks=expected_blank_fks)

        invoice_retrieve_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
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
        autospec=True,
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_II),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
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
    def test_sync_expanded_invoice_with_subscription(
        self,
        invoice_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        paymentintent_retrieve_mock,
        paymentmethod_retrieve_mock,
        subscription_retrieve_mock,
        product_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_II)
        fake_payment_intent["invoice"] = FAKE_INVOICE_II["id"]
        paymentintent_retrieve_mock.return_value = fake_payment_intent

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION_III)
        fake_subscription["latest_invoice"] = FAKE_INVOICE_II["id"]
        subscription_retrieve_mock.return_value = fake_subscription

        fake_card = deepcopy(FAKE_CARD_II)
        fake_card["customer"] = None
        # create Card for FAKE_CUSTOMER_III
        Card.sync_from_stripe_data(fake_card)

        # create invoice
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE_II))

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
            "djstripe.InvoiceItem.plan",
            "djstripe.InvoiceItem.price",
        }
        expected_blank_fks.difference_update(
            {
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.Invoice.payment_intent",
            }
        )

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
    @patch("stripe.Price.retrieve", return_value=deepcopy(FAKE_PRICE_II), autospec=True)
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN_II), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_II),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
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
        paymentintent_retrieve_mock,
        paymentmethod_retrieve_mock,
        subscription_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        price_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_II)
        fake_payment_intent["invoice"] = FAKE_INVOICE_II["id"]
        paymentintent_retrieve_mock.return_value = fake_payment_intent

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION_III)
        fake_subscription["latest_invoice"] = FAKE_INVOICE_II["id"]
        subscription_retrieve_mock.return_value = fake_subscription

        fake_card = deepcopy(FAKE_CARD_II)
        fake_card["customer"] = None
        # create Card for FAKE_CUSTOMER_III
        Card.sync_from_stripe_data(fake_card)

        # create invoice
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE_II))

        default_account_mock.return_value = self.account

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

        expected_blank_fks = self.default_expected_blank_fks | {
            "djstripe.InvoiceItem.subscription"
        }
        expected_blank_fks.difference_update(
            {
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.Invoice.payment_intent",
            }
        )

        self.assert_fks(
            invoiceitem,
            expected_blank_fks=expected_blank_fks,
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch("stripe.Price.retrieve", return_value=deepcopy(FAKE_PRICE_II), autospec=True)
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
        price_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

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
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_II),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II), autospec=True
    )
    def test_sync_with_taxes(
        self,
        invoice_retrieve_mock,
        paymentintent_retrieve_mock,
        paymentmethod_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        product_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_II)
        fake_payment_intent["invoice"] = FAKE_INVOICE_II["id"]
        paymentintent_retrieve_mock.return_value = fake_payment_intent

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION_III)
        fake_subscription["latest_invoice"] = FAKE_INVOICE_II["id"]
        subscription_retrieve_mock.return_value = fake_subscription

        fake_card = deepcopy(FAKE_CARD_II)
        fake_card["customer"] = None
        # create Card for FAKE_CUSTOMER_III
        Card.sync_from_stripe_data(fake_card)

        # create invoice
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE_II))

        default_account_mock.return_value = self.account

        invoiceitem_data = deepcopy(FAKE_INVOICEITEM_III)
        invoiceitem_data["plan"] = FAKE_PLAN_II
        invoiceitem_data["price"] = FAKE_PRICE_II
        invoiceitem = InvoiceItem.sync_from_stripe_data(invoiceitem_data)

        self.assertEqual(invoiceitem.tax_rates.count(), 1)
        self.assertEqual(
            invoiceitem.tax_rates.first().id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )
