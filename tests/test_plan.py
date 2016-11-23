"""
.. module:: dj-stripe.tests.test_plan
   :synopsis: dj-stripe Plan Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy

from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from mock import patch

from djstripe.admin import PlanAdmin
from djstripe.models import Plan
from tests import FAKE_PLAN, FAKE_PLAN_II


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
        self.assertEqual("<name={name}, stripe_id={stripe_id}>".format(name=self.plan_data["name"], stripe_id=self.plan_data["id"]), str(self.plan))

    @patch("stripe.Plan.retrieve", return_value="soup")
    def test_stripe_plan(self, plan_retrieve_mock):
        self.assertEqual("soup", self.plan.api_retrieve())
        plan_retrieve_mock.assert_called_once_with(id=self.plan_data["id"], api_key=settings.STRIPE_SECRET_KEY,
                                                   expand=None)
