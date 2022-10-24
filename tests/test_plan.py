"""
dj-stripe Plan Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
import stripe
from django.test import TestCase

from djstripe.enums import PriceUsageType
from djstripe.models import Plan, Product, Subscription
from djstripe.settings import djstripe_settings

from . import (
    FAKE_PLAN,
    FAKE_PLAN_II,
    FAKE_PLAN_METERED,
    FAKE_PRODUCT,
    FAKE_TIER_PLAN,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


class PlanCreateTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        with patch(
            "stripe.Product.retrieve",
            return_value=deepcopy(FAKE_PRODUCT),
            autospec=True,
        ):
            self.stripe_product = Product(id=FAKE_PRODUCT["id"]).api_retrieve()

    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch("stripe.Plan.create", return_value=deepcopy(FAKE_PLAN), autospec=True)
    def test_create_from_product_id(self, plan_create_mock, product_retrieve_mock):
        fake_plan = deepcopy(FAKE_PLAN)
        fake_plan["amount"] = fake_plan["amount"] / 100
        self.assertIsInstance(fake_plan["product"], str)

        plan = Plan.create(**fake_plan)

        expected_create_kwargs = deepcopy(FAKE_PLAN)
        expected_create_kwargs["api_key"] = djstripe_settings.STRIPE_SECRET_KEY

        plan_create_mock.assert_called_once_with(**expected_create_kwargs)

        self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})

    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch("stripe.Plan.create", return_value=deepcopy(FAKE_PLAN), autospec=True)
    def test_create_from_stripe_product(self, plan_create_mock, product_retrieve_mock):
        fake_plan = deepcopy(FAKE_PLAN)
        fake_plan["product"] = self.stripe_product
        fake_plan["amount"] = fake_plan["amount"] / 100
        self.assertIsInstance(fake_plan["product"], dict)

        plan = Plan.create(**fake_plan)

        expected_create_kwargs = deepcopy(FAKE_PLAN)
        expected_create_kwargs["product"] = self.stripe_product

        plan_create_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY, **expected_create_kwargs
        )

        self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})

    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch("stripe.Plan.create", return_value=deepcopy(FAKE_PLAN), autospec=True)
    def test_create_from_djstripe_product(
        self, plan_create_mock, product_retrieve_mock
    ):
        fake_plan = deepcopy(FAKE_PLAN)
        fake_plan["product"] = Product.sync_from_stripe_data(self.stripe_product)
        fake_plan["amount"] = fake_plan["amount"] / 100
        self.assertIsInstance(fake_plan["product"], Product)

        plan = Plan.create(**fake_plan)

        plan_create_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY, **FAKE_PLAN
        )

        self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})

    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch("stripe.Plan.create", return_value=deepcopy(FAKE_PLAN), autospec=True)
    def test_create_with_metadata(self, plan_create_mock, product_retrieve_mock):
        metadata = {"other_data": "more_data"}
        fake_plan = deepcopy(FAKE_PLAN)
        fake_plan["amount"] = fake_plan["amount"] / 100
        fake_plan["metadata"] = metadata
        self.assertIsInstance(fake_plan["product"], str)

        plan = Plan.create(**fake_plan)

        expected_create_kwargs = deepcopy(FAKE_PLAN)
        expected_create_kwargs["metadata"] = metadata

        plan_create_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY, **expected_create_kwargs
        )

        self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})


class PlanTest(AssertStripeFksMixin, TestCase):
    plan: Plan

    def setUp(self):
        self.plan_data = deepcopy(FAKE_PLAN)
        with patch(
            "stripe.Product.retrieve",
            return_value=deepcopy(FAKE_PRODUCT),
            autospec=True,
        ):
            self.plan = Plan.sync_from_stripe_data(self.plan_data)

    def test___str__(self):
        assert (
            str(self.plan)
            == f"{self.plan.human_readable_price} for {FAKE_PRODUCT['name']}"
        )

    def test___str__null_product(self):
        plan_data = deepcopy(FAKE_PLAN_II)
        del plan_data["product"]
        plan: Plan = Plan.sync_from_stripe_data(plan_data)

        self.assertIsNone(plan.product)

        assert str(plan) == plan.human_readable_price

    @patch("stripe.Plan.retrieve", return_value=FAKE_PLAN, autospec=True)
    def test_stripe_plan(self, plan_retrieve_mock):
        stripe_plan = self.plan.api_retrieve()
        plan_retrieve_mock.assert_called_once_with(
            id=self.plan_data["id"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            expand=["product", "tiers"],
            stripe_account=self.plan.djstripe_owner_account.id,
        )
        plan = Plan.sync_from_stripe_data(stripe_plan)
        assert plan.amount_in_cents == plan.amount * 100
        assert isinstance(plan.amount_in_cents, int)

        self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})

    def test_stripe_plan_null_product(self):
        """
        assert that plan.Product can be null for backwards compatibility
        though note that it is a Stripe required field
        """
        plan_data = deepcopy(FAKE_PLAN_II)
        del plan_data["product"]
        plan = Plan.sync_from_stripe_data(plan_data)

        self.assert_fks(
            plan,
            expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
        )

    def test_stripe_tier_plan(self):
        tier_plan_data = deepcopy(FAKE_TIER_PLAN)
        plan = Plan.sync_from_stripe_data(tier_plan_data)

        self.assertEqual(plan.id, tier_plan_data["id"])
        self.assertIsNone(plan.amount)
        self.assertIsNotNone(plan.tiers, plan.product)

        self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})

    def test_stripe_metered_plan(self):
        plan_data = deepcopy(FAKE_PLAN_METERED)
        plan = Plan.sync_from_stripe_data(plan_data)
        self.assertEqual(plan.id, plan_data["id"])
        self.assertEqual(plan.usage_type, PriceUsageType.metered)
        self.assertIsNotNone(plan.amount, plan.product)

        self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})


class TestHumanReadablePlan:

    #
    # Helpers
    #
    def get_fake_price_NONE_flat_amount():
        FAKE_PRICE_TIER_NONE_FLAT_AMOUNT = deepcopy(FAKE_TIER_PLAN)
        FAKE_PRICE_TIER_NONE_FLAT_AMOUNT["tiers"][0]["flat_amount"] = None
        FAKE_PRICE_TIER_NONE_FLAT_AMOUNT["tiers"][0]["flat_amount_decimal"] = None
        return FAKE_PRICE_TIER_NONE_FLAT_AMOUNT

    def get_fake_price_0_flat_amount():
        FAKE_PRICE_TIER_0_FLAT_AMOUNT = deepcopy(FAKE_TIER_PLAN)
        FAKE_PRICE_TIER_0_FLAT_AMOUNT["tiers"][0]["flat_amount"] = 0
        FAKE_PRICE_TIER_0_FLAT_AMOUNT["tiers"][0]["flat_amount_decimal"] = 0
        return FAKE_PRICE_TIER_0_FLAT_AMOUNT

    def get_fake_price_0_amount():
        FAKE_PRICE_TIER_0_AMOUNT = deepcopy(FAKE_PLAN)
        FAKE_PRICE_TIER_0_AMOUNT["amount"] = 0
        FAKE_PRICE_TIER_0_AMOUNT["amount_decimal"] = 0
        return FAKE_PRICE_TIER_0_AMOUNT

    @pytest.mark.parametrize(
        "fake_plan_data, expected_str",
        [
            (deepcopy(FAKE_PLAN), "$20.00 USD/month"),
            (get_fake_price_0_amount(), "$0.00 USD/month"),
            (
                deepcopy(FAKE_TIER_PLAN),
                "Starts at $10.00 USD per unit + $49.00 USD/month",
            ),
            (
                get_fake_price_0_flat_amount(),
                "Starts at $10.00 USD per unit + $0.00 USD/month",
            ),
            (
                get_fake_price_NONE_flat_amount(),
                "Starts at $10.00 USD per unit/month",
            ),
            (deepcopy(FAKE_PLAN_METERED), "$2.00 USD/month"),
        ],
    )
    def test_human_readable(self, fake_plan_data, expected_str, monkeypatch):
        def mock_product_get(*args, **kwargs):
            return deepcopy(FAKE_PRODUCT)

        def mock_price_get(*args, **kwargs):
            return fake_plan_data

        # monkeypatch stripe.Product.retrieve and stripe.Plan.retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Product, "retrieve", mock_product_get)
        monkeypatch.setattr(stripe.Plan, "retrieve", mock_price_get)

        plan = Plan.sync_from_stripe_data(fake_plan_data)

        assert plan.human_readable_price == expected_str
