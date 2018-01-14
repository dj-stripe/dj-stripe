"""
.. module:: dj-stripe.tests.test_plan
   :synopsis: dj-stripe Plan Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

from copy import deepcopy
from decimal import Decimal

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from mock import patch

from djstripe.admin import PlanAdmin
from djstripe.models import Plan

from . import FAKE_PLAN, FAKE_PLAN_II


class TestPlanAdmin(TestCase):

    class FakeForm(object):
        cleaned_data = {}

    class FakeRequest(object):
        pass

    def setUp(self):
        self.plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))
        self.site = AdminSite()
        self.plan_admin = PlanAdmin(Plan, self.site)

    @patch("stripe.Plan.retrieve")
    def test_update_name(self, plan_retrieve_mock):
        new_name = 'Updated Plan Name'

        self.plan.name = new_name
        self.plan.update_name()

        # Would throw DoesNotExist if it didn't work
        Plan.objects.get(name='Updated Plan Name')

    @patch("stripe.Plan.create")
    @patch("stripe.Plan.retrieve")
    def test_that_admin_save_does_create_new_object(self, plan_retrieve_mock, plan_create_mock):
        fake_form = self.FakeForm()
        plan_data = Plan._stripe_object_to_record(deepcopy(FAKE_PLAN_II))

        fake_form.cleaned_data = plan_data

        self.plan_admin.save_model(request=self.FakeRequest(), obj=None, form=fake_form, change=False)

        # Would throw DoesNotExist if it didn't work
        Plan.objects.get(stripe_id=plan_data["stripe_id"])

    @patch("stripe.Plan.create")
    @patch("stripe.Plan.retrieve")
    def test_that_admin_save_does_update_object(self, plan_retrieve_mock, plan_create_mock):
        self.plan.name = 'A new name (again)'

        self.plan_admin.save_model(request=self.FakeRequest(), obj=self.plan,
                                   form=self.FakeForm(), change=True)

        # Would throw DoesNotExist if it didn't work
        Plan.objects.get(name=self.plan.name)


class PlanTest(TestCase):

    def setUp(self):
        self.plan_data = deepcopy(FAKE_PLAN)
        self.plan = Plan.sync_from_stripe_data(self.plan_data)

    @patch("djstripe.models.Plan.objects.create")
    @patch("djstripe.models.Plan._api_create")
    def test_create_with_metadata(self, api_create_mock, object_create_mock):
        metadata = {'other_data': 'more_data'}
        Plan.create(metadata=metadata, arg1=1, arg2=2, amount=1, stripe_id=1)

        api_create_mock.assert_called_once_with(metadata=metadata, id=1, arg1=1, arg2=2, amount=100)
        object_create_mock.assert_called_once_with(metadata=metadata, stripe_id=1, arg1=1, arg2=2, amount=1)

    def test_str(self):
        self.assertEqual(str(self.plan), self.plan_data["name"])

    @patch("stripe.Plan.retrieve", return_value=FAKE_PLAN)
    def test_stripe_plan(self, plan_retrieve_mock):
        stripe_plan = self.plan.api_retrieve()
        plan_retrieve_mock.assert_called_once_with(
            id=self.plan_data["id"],
            api_key=settings.STRIPE_SECRET_KEY,
            expand=None
        )
        plan = Plan.sync_from_stripe_data(stripe_plan)
        assert plan.amount_in_cents == plan.amount * 100
        assert isinstance(plan.amount_in_cents, int)


class HumanReadablePlanTest(TestCase):
    def test_human_readable_free_usd_daily(self):
        plan = Plan.objects.create(
            stripe_id="plan-test-free-usd-daily", amount=0, currency="usd",
            interval="day", interval_count=1,
        )
        self.assertEqual(plan.human_readable_price, "$0.00 USD/day")

    def test_human_readable_10_usd_weekly(self):
        plan = Plan.objects.create(
            stripe_id="plan-test-10-usd-weekly", amount=10, currency="usd",
            interval="week", interval_count=1,
        )
        self.assertEqual(plan.human_readable_price, "$10.00 USD/week")

    def test_human_readable_10_usd_2weeks(self):
        plan = Plan.objects.create(
            stripe_id="plan-test-10-usd-2w", amount=10, currency="usd",
            interval="week", interval_count=2,
        )
        self.assertEqual(plan.human_readable_price, "$10.00 USD every 2 weeks")

    def test_human_readable_499_usd_monthly(self):
        plan = Plan.objects.create(
            stripe_id="plan-test-499-usd-monthly", amount=Decimal("4.99"), currency="usd",
            interval="month", interval_count=1,
        )
        self.assertEqual(plan.human_readable_price, "$4.99 USD/month")

    def test_human_readable_25_usd_6months(self):
        plan = Plan.objects.create(
            stripe_id="plan-test-25-usd-6m", amount=25, currency="usd",
            interval="month", interval_count=6,
        )
        self.assertEqual(plan.human_readable_price, "$25.00 USD every 6 months")

    def test_human_readable_10_usd_yearly(self):
        plan = Plan.objects.create(
            stripe_id="plan-test-10-usd-yearly", amount=10, currency="usd",
            interval="year", interval_count=1,
        )
        self.assertEqual(plan.human_readable_price, "$10.00 USD/year")
