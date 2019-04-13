"""
dj-stripe Plan Model Tests.
"""
from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from djstripe.admin import PlanAdmin
from djstripe.enums import PlanUsageType
from djstripe.models import Plan, Product
from djstripe.settings import STRIPE_SECRET_KEY

from . import (
	FAKE_PLAN, FAKE_PLAN_II, FAKE_PLAN_METERED,
	FAKE_PRODUCT, FAKE_TIER_PLAN, AssertStripeFksMixin
)


class TestPlanAdmin(TestCase):
	class FakeForm(object):
		cleaned_data = {}

	class FakeRequest(object):
		pass

	def setUp(self):
		with patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT)):
			self.plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

		self.site = AdminSite()
		self.plan_admin = PlanAdmin(Plan, self.site)

	@patch("stripe.Plan.retrieve")
	def test_update_name(self, plan_retrieve_mock):
		new_name = "Updated Plan Name"

		self.plan.name = new_name
		self.plan.update_name()

		# Would throw DoesNotExist if it didn't work
		Plan.objects.get(name="Updated Plan Name")

	@patch("stripe.Plan.create", return_value=FAKE_PLAN_II)
	@patch("stripe.Plan.retrieve")
	def test_that_admin_save_does_create_new_object(
		self, plan_retrieve_mock, plan_create_mock
	):
		fake_form = self.FakeForm()
		plan_data = Plan._stripe_object_to_record(deepcopy(FAKE_PLAN_II))

		fake_form.cleaned_data = plan_data

		self.plan_admin.save_model(
			request=self.FakeRequest(), obj=None, form=fake_form, change=False
		)

		# Would throw DoesNotExist if it didn't work
		Plan.objects.get(id=plan_data["id"])

	@patch("stripe.Plan.create")
	@patch("stripe.Plan.retrieve")
	def test_that_admin_save_does_update_object(
		self, plan_retrieve_mock, plan_create_mock
	):
		self.plan.name = "A new name (again)"

		self.plan_admin.save_model(
			request=self.FakeRequest(), obj=self.plan, form=self.FakeForm(), change=True
		)

		# Would throw DoesNotExist if it didn't work
		Plan.objects.get(name=self.plan.name)


class PlanCreateTest(AssertStripeFksMixin, TestCase):
	def setUp(self):
		with patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT)):
			self.stripe_product = Product(id=FAKE_PRODUCT["id"]).api_retrieve()

	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT))
	@patch("stripe.Plan.create", return_value=deepcopy(FAKE_PLAN))
	def test_create_from_product_id(self, plan_create_mock, product_retrieve_mock):
		fake_plan = deepcopy(FAKE_PLAN)
		fake_plan["amount"] = fake_plan["amount"] / 100
		self.assertIsInstance(fake_plan["product"], str)

		plan = Plan.create(**fake_plan)

		expected_create_kwargs = deepcopy(FAKE_PLAN)
		expected_create_kwargs["api_key"] = STRIPE_SECRET_KEY

		plan_create_mock.assert_called_once_with(**expected_create_kwargs)

		self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})

	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT))
	@patch("stripe.Plan.create", return_value=deepcopy(FAKE_PLAN))
	def test_create_from_stripe_product(self, plan_create_mock, product_retrieve_mock):
		fake_plan = deepcopy(FAKE_PLAN)
		fake_plan["product"] = self.stripe_product
		fake_plan["amount"] = fake_plan["amount"] / 100
		self.assertIsInstance(fake_plan["product"], dict)

		plan = Plan.create(**fake_plan)

		expected_create_kwargs = deepcopy(FAKE_PLAN)
		expected_create_kwargs["product"] = self.stripe_product

		plan_create_mock.assert_called_once_with(
			api_key=STRIPE_SECRET_KEY, **expected_create_kwargs
		)

		self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})

	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT))
	@patch("stripe.Plan.create", return_value=deepcopy(FAKE_PLAN))
	def test_create_from_djstripe_product(self, plan_create_mock, product_retrieve_mock):
		fake_plan = deepcopy(FAKE_PLAN)
		fake_plan["product"] = Product.sync_from_stripe_data(self.stripe_product)
		fake_plan["amount"] = fake_plan["amount"] / 100
		self.assertIsInstance(fake_plan["product"], Product)

		plan = Plan.create(**fake_plan)

		plan_create_mock.assert_called_once_with(api_key=STRIPE_SECRET_KEY, **FAKE_PLAN)

		self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})

	@patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT))
	@patch("stripe.Plan.create", return_value=deepcopy(FAKE_PLAN))
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
			api_key=STRIPE_SECRET_KEY, **expected_create_kwargs
		)

		self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})


class PlanTest(AssertStripeFksMixin, TestCase):
	def setUp(self):
		self.plan_data = deepcopy(FAKE_PLAN)
		with patch("stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT)):
			self.plan = Plan.sync_from_stripe_data(self.plan_data)

	def test_str(self):
		self.assertEqual(str(self.plan), self.plan_data["name"])

	@patch("stripe.Plan.retrieve", return_value=FAKE_PLAN)
	def test_stripe_plan(self, plan_retrieve_mock):
		stripe_plan = self.plan.api_retrieve()
		plan_retrieve_mock.assert_called_once_with(
			id=self.plan_data["id"], api_key=STRIPE_SECRET_KEY, expand=[]
		)
		plan = Plan.sync_from_stripe_data(stripe_plan)
		assert plan.amount_in_cents == plan.amount * 100
		assert isinstance(plan.amount_in_cents, int)

		self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})

	@patch("stripe.Product.retrieve")
	def test_stripe_plan_null_product(self, product_retrieve_mock):
		"""
		assert that plan.Product can be null for backwards compatibility
		though note that it is a Stripe required field
		"""
		plan_data = deepcopy(FAKE_PLAN_II)
		del plan_data["product"]
		plan = Plan.sync_from_stripe_data(plan_data)

		self.assert_fks(
			plan, expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"}
		)

	@patch("stripe.Plan.retrieve")
	def test_stripe_tier_plan(self, plan_retrieve_mock):
		tier_plan_data = deepcopy(FAKE_TIER_PLAN)
		plan = Plan.sync_from_stripe_data(tier_plan_data)
		self.assertEqual(plan.id, tier_plan_data["id"])
		self.assertIsNone(plan.amount)
		self.assertIsNotNone(plan.tiers)

		self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})

	@patch("stripe.Plan.retrieve")
	def test_stripe_metered_plan(self, plan_retrieve_mock):
		plan_data = deepcopy(FAKE_PLAN_METERED)
		plan = Plan.sync_from_stripe_data(plan_data)
		self.assertEqual(plan.id, plan_data["id"])
		self.assertEqual(plan.usage_type, PlanUsageType.metered)
		self.assertIsNotNone(plan.amount)

		self.assert_fks(plan, expected_blank_fks={"djstripe.Customer.coupon"})


class HumanReadablePlanTest(TestCase):
	def test_human_readable_free_usd_daily(self):
		plan = Plan.objects.create(
			id="plan-test-free-usd-daily",
			active=True,
			amount=0,
			currency="usd",
			interval="day",
			interval_count=1,
		)
		self.assertEqual(plan.human_readable_price, "$0.00 USD/day")

	def test_human_readable_10_usd_weekly(self):
		plan = Plan.objects.create(
			id="plan-test-10-usd-weekly",
			active=True,
			amount=10,
			currency="usd",
			interval="week",
			interval_count=1,
		)
		self.assertEqual(plan.human_readable_price, "$10.00 USD/week")

	def test_human_readable_10_usd_2weeks(self):
		plan = Plan.objects.create(
			id="plan-test-10-usd-2w",
			active=True,
			amount=10,
			currency="usd",
			interval="week",
			interval_count=2,
		)
		self.assertEqual(plan.human_readable_price, "$10.00 USD every 2 weeks")

	def test_human_readable_499_usd_monthly(self):
		plan = Plan.objects.create(
			id="plan-test-499-usd-monthly",
			active=True,
			amount=Decimal("4.99"),
			currency="usd",
			interval="month",
			interval_count=1,
		)
		self.assertEqual(plan.human_readable_price, "$4.99 USD/month")

	def test_human_readable_25_usd_6months(self):
		plan = Plan.objects.create(
			id="plan-test-25-usd-6m",
			active=True,
			amount=25,
			currency="usd",
			interval="month",
			interval_count=6,
		)
		self.assertEqual(plan.human_readable_price, "$25.00 USD every 6 months")

	def test_human_readable_10_usd_yearly(self):
		plan = Plan.objects.create(
			id="plan-test-10-usd-yearly",
			active=True,
			amount=10,
			currency="usd",
			interval="year",
			interval_count=1,
		)
		self.assertEqual(plan.human_readable_price, "$10.00 USD/year")
