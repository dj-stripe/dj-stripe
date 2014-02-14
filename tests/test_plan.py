from django.test import TestCase
from djstripe.models import Plan
from djstripe.admin import PlanAdmin
from django.contrib.admin.sites import AdminSite

from mock import patch


class MockRequest(object):
    pass


class MockForm(object):
    cleaned_data = {}


class TestPlan(TestCase):

    def setUp(self):
        self.plan = Plan.objects.create(
            stripe_id='teststripeid',
            amount=25000,
            currency='usd',
            interval='week',
            interval_count=1,
            name='A test Stripe Plan',
            trial_period_days=12
        )
        self.site = AdminSite()
        self.plan_admin = PlanAdmin(Plan, self.site)

    @patch("stripe.Plan.retrieve")
    def test_update_name_does_update(self, RetrieveMock):

        self.plan.name = 'a_new_name'
        self.plan.update_name()

        Plan.objects.get(name='a_new_name')

    @patch("stripe.Plan.create")
    @patch("stripe.Plan.retrieve")
    def test_that_admin_save_does_create_new_object(self, RetrieveMock, CreateMock):

        form = MockForm()
        stripe_id = 'admintestid'
        form.cleaned_data = {
            'stripe_id': stripe_id,
            'amount': 25000,
            'currency': 'usd',
            'interval': 'month',
            'interval_count': 1,
            'name': 'A test Admin Stripe Plan',
            'trial_period_days': 12
        }

        self.plan_admin.save_model(request=MockRequest(), obj=None,
                                   form=form, change=False)

        Plan.objects.get(stripe_id=stripe_id)

    @patch("stripe.Plan.create")
    @patch("stripe.Plan.retrieve")
    def test_that_admin_save_does_update_object(self, RetrieveMock, CreateMock):

        self.plan.name = 'A new name'

        self.plan_admin.save_model(request=MockRequest(), obj=self.plan,
                                   form=MockForm(), change=True)

        Plan.objects.get(name=self.plan.name)
