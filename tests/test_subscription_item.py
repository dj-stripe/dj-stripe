"""
dj-stripe SubscriptionItem model tests
"""
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe.models import SubscriptionItem
from djstripe.models.billing import Invoice

from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_CUSTOMER_II,
    FAKE_INVOICE,
    FAKE_INVOICEITEM,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PLAN,
    FAKE_PLAN_II,
    FAKE_PLAN_METERED,
    FAKE_PRICE,
    FAKE_PRICE_II,
    FAKE_PRICE_METERED,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_II,
    FAKE_SUBSCRIPTION_ITEM,
    FAKE_SUBSCRIPTION_ITEM_METERED,
    FAKE_SUBSCRIPTION_ITEM_MULTI_PLAN,
    FAKE_SUBSCRIPTION_ITEM_TAX_RATES,
    FAKE_SUBSCRIPTION_METERED,
    FAKE_SUBSCRIPTION_MULTI_PLAN,
    FAKE_TAX_RATE_EXAMPLE_1_VAT,
    AssertStripeFksMixin,
)


class SubscriptionItemTest(AssertStripeFksMixin, TestCase):
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
    def setUp(
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
        customer_retrieve_mock,
    ):
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

        self.default_expected_blank_fks = {
            "djstripe.Customer.coupon",
            "djstripe.Customer.default_payment_method",
            "djstripe.Product.default_price",
            "djstripe.Subscription.default_payment_method",
            "djstripe.Subscription.default_source",
            "djstripe.Subscription.pending_setup_intent",
            "djstripe.Subscription.schedule",
        }
        # create latest invoice
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

    @patch(
        "stripe.Price.retrieve",
        return_value=deepcopy(FAKE_PRICE_METERED),
        autospec=True,
    )
    @patch(
        "stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN_METERED), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_METERED),
        autospec=True,
    )
    def test_sync_from_stripe_data_metered_subscription(
        self,
        subscription_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        price_retrieve_mock,
    ):
        subscription_item_fake = deepcopy(FAKE_SUBSCRIPTION_ITEM_METERED)
        subscription_item = SubscriptionItem.sync_from_stripe_data(
            subscription_item_fake
        )

        self.assertEqual(subscription_item.id, FAKE_SUBSCRIPTION_ITEM_METERED["id"])
        self.assertEqual(
            subscription_item.plan.id, FAKE_SUBSCRIPTION_ITEM_METERED["plan"]["id"]
        )
        self.assertEqual(
            subscription_item.price.id, FAKE_SUBSCRIPTION_ITEM_METERED["price"]["id"]
        )
        self.assertEqual(
            subscription_item.subscription.id,
            FAKE_SUBSCRIPTION_ITEM_METERED["subscription"],
        )

        self.assert_fks(
            subscription_item,
            expected_blank_fks=(
                self.default_expected_blank_fks
                | {"djstripe.Subscription.latest_invoice"}
            ),
        )

    @patch(
        "stripe.Price.retrieve",
        return_value=deepcopy(FAKE_PRICE_II),
        autospec=True,
    )
    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN_II), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        autospec=True,
    )
    def test_sync_items_with_tax_rates(
        self,
        subscription_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        price_retrieve_mock,
    ):

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION_II)
        fake_subscription["latest_invoice"] = FAKE_INVOICE["id"]
        subscription_retrieve_mock.return_value = fake_subscription

        subscription_item_fake = deepcopy(FAKE_SUBSCRIPTION_ITEM_TAX_RATES)
        subscription_item = SubscriptionItem.sync_from_stripe_data(
            subscription_item_fake
        )

        self.assertEqual(subscription_item.id, FAKE_SUBSCRIPTION_ITEM_TAX_RATES["id"])
        self.assertEqual(
            subscription_item.plan.id, FAKE_SUBSCRIPTION_ITEM_TAX_RATES["plan"]["id"]
        )
        self.assertEqual(
            subscription_item.price.id, FAKE_SUBSCRIPTION_ITEM_TAX_RATES["price"]["id"]
        )
        self.assertEqual(
            subscription_item.subscription.id,
            FAKE_SUBSCRIPTION_ITEM_TAX_RATES["subscription"],
        )

        self.assert_fks(
            subscription_item,
            expected_blank_fks=(
                self.default_expected_blank_fks
                | {
                    "djstripe.Charge.latest_upcominginvoice (related name)",
                    "djstripe.Charge.application_fee",
                    "djstripe.Charge.dispute",
                    "djstripe.Charge.on_behalf_of",
                    "djstripe.Charge.source_transfer",
                    "djstripe.Charge.transfer",
                    "djstripe.PaymentIntent.upcominginvoice (related name)",
                    "djstripe.PaymentIntent.on_behalf_of",
                    "djstripe.PaymentIntent.payment_method",
                    "djstripe.Invoice.default_payment_method",
                    "djstripe.Invoice.default_source",
                }
            ),
        )

        self.assertEqual(subscription_item.tax_rates.count(), 1)
        self.assertEqual(
            subscription_item.tax_rates.first().id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )

    @patch(
        "stripe.Price.retrieve",
        side_effect=[deepcopy(FAKE_PRICE), deepcopy(FAKE_PRICE_II)],
        autospec=True,
    )
    @patch(
        "stripe.Plan.retrieve",
        side_effect=[deepcopy(FAKE_PLAN), deepcopy(FAKE_PLAN_II)],
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        autospec=True,
    )
    def test_sync_multi_plan_subscription(
        self,
        subscription_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        price_retrieve_mock,
    ):

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION_MULTI_PLAN)
        fake_subscription["latest_invoice"] = FAKE_INVOICE["id"]
        subscription_retrieve_mock.return_value = fake_subscription

        subscription_item_fake = deepcopy(FAKE_SUBSCRIPTION_ITEM_MULTI_PLAN)
        subscription_item = SubscriptionItem.sync_from_stripe_data(
            subscription_item_fake
        )

        self.assertEqual(subscription_item.id, FAKE_SUBSCRIPTION_ITEM_MULTI_PLAN["id"])
        self.assertEqual(
            subscription_item.plan.id, FAKE_SUBSCRIPTION_ITEM_MULTI_PLAN["plan"]["id"]
        )
        self.assertEqual(
            subscription_item.price.id, FAKE_SUBSCRIPTION_ITEM_MULTI_PLAN["price"]["id"]
        )
        self.assertEqual(
            subscription_item.subscription.id,
            FAKE_SUBSCRIPTION_ITEM_MULTI_PLAN["subscription"],
        )

        # delete pydanny customer as that causes issues with Invoice and Latest_invoice FKs
        self.customer.delete()

        self.assert_fks(
            subscription_item,
            expected_blank_fks=(
                self.default_expected_blank_fks
                | {
                    "djstripe.Customer.subscriber",
                    "djstripe.Subscription.plan",
                    "djstripe.Charge.latest_upcominginvoice (related name)",
                    "djstripe.Charge.application_fee",
                    "djstripe.Charge.dispute",
                    "djstripe.Charge.on_behalf_of",
                    "djstripe.Charge.source_transfer",
                    "djstripe.Charge.transfer",
                    "djstripe.PaymentIntent.upcominginvoice (related name)",
                    "djstripe.PaymentIntent.on_behalf_of",
                    "djstripe.PaymentIntent.payment_method",
                    "djstripe.Invoice.default_payment_method",
                    "djstripe.Invoice.default_source",
                    "djstripe.Invoice.charge",
                    "djstripe.Invoice.customer",
                    "djstripe.Invoice.payment_intent",
                    "djstripe.Invoice.subscription",
                }
            ),
        )
