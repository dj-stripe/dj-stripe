"""
dj-stripe SubscriptionItem model tests
"""
from copy import copy, deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe.models import SubscriptionItem

from . import (
    FAKE_CUSTOMER,
    FAKE_CUSTOMER_II,
    FAKE_PLAN,
    FAKE_PLAN_II,
    FAKE_PLAN_METERED,
    FAKE_PRICE,
    FAKE_PRICE_II,
    FAKE_PRICE_METERED,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION_II,
    FAKE_SUBSCRIPTION_ITEM_METERED,
    FAKE_SUBSCRIPTION_ITEM_MULTI_PLAN,
    FAKE_SUBSCRIPTION_ITEM_TAX_RATES,
    FAKE_SUBSCRIPTION_METERED,
    FAKE_SUBSCRIPTION_MULTI_PLAN,
    FAKE_TAX_RATE_EXAMPLE_1_VAT,
    AssertStripeFksMixin,
)


class SubscriptionItemTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

        self.default_expected_blank_fks = {
            "djstripe.Customer.coupon",
            "djstripe.Customer.default_payment_method",
            "djstripe.Subscription.default_payment_method",
            "djstripe.Subscription.default_source",
            "djstripe.Subscription.pending_setup_intent",
            "djstripe.Subscription.schedule",
        }

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
            subscription_item, expected_blank_fks=self.default_expected_blank_fks
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
        return_value=deepcopy(FAKE_SUBSCRIPTION_II),
    )
    def test_sync_items_with_tax_rates(
        self,
        subscription_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        price_retrieve_mock,
    ):

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
            subscription_item, expected_blank_fks=self.default_expected_blank_fks
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
        return_value=deepcopy(FAKE_SUBSCRIPTION_MULTI_PLAN),
    )
    def test_sync_multi_plan_subscription(
        self,
        subscription_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        price_retrieve_mock,
    ):

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

        expected_blank_fks = copy(self.default_expected_blank_fks)
        expected_blank_fks.update(
            {"djstripe.Customer.subscriber", "djstripe.Subscription.plan"}
        )

        self.assert_fks(subscription_item, expected_blank_fks=expected_blank_fks)
