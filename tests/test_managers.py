"""
.. module:: dj-stripe.tests.test_managers
   :synopsis: dj-stripe Model Manager Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import decimal
from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from djstripe.models import Charge, Customer, Plan, Subscription, Transfer

from . import FAKE_PLAN, FAKE_PLAN_II, FAKE_TRANSFER, FAKE_TRANSFER_II, FAKE_TRANSFER_III


class SubscriptionManagerTest(TestCase):

    def setUp(self):
        # create customers and current subscription records
        period_start = datetime.datetime(2013, 4, 1, tzinfo=timezone.utc)
        period_end = datetime.datetime(2013, 4, 30, tzinfo=timezone.utc)
        start = datetime.datetime(2013, 1, 1, 0, 0, 1, tzinfo=timezone.utc)  # more realistic start

        self.plan = Plan.sync_from_stripe_data(FAKE_PLAN)
        self.plan2 = Plan.sync_from_stripe_data(FAKE_PLAN_II)

        for i in range(10):
            user = get_user_model().objects.create_user(
                username="patrick{0}".format(i),
                email="patrick{0}@example.com".format(i)
            )
            customer = Customer.objects.create(
                subscriber=user,
                stripe_id="cus_xxxxxxxxxxxxxx{0}".format(i),
                livemode=False,
                account_balance=0,
                delinquent=False,
            )

            Subscription.objects.create(
                stripe_id="sub_xxxxxxxxxxxxxx{0}".format(i),
                customer=customer,
                plan=self.plan,
                current_period_start=period_start,
                current_period_end=period_end,
                status="active",
                start=start,
                quantity=1
            )

        user = get_user_model().objects.create_user(
            username="patrick{0}".format(11),
            email="patrick{0}@example.com".format(11)
        )
        customer = Customer.objects.create(
            subscriber=user,
            stripe_id="cus_xxxxxxxxxxxxxx{0}".format(11),
            livemode=False,
            account_balance=0,
            delinquent=False,
        )
        Subscription.objects.create(
            stripe_id="sub_xxxxxxxxxxxxxx{0}".format(11),
            customer=customer,
            plan=self.plan,
            current_period_start=period_start,
            current_period_end=period_end,
            status="canceled",
            canceled_at=period_end,
            start=start,
            quantity=1
        )

        user = get_user_model().objects.create_user(
            username="patrick{0}".format(12),
            email="patrick{0}@example.com".format(12)
        )
        customer = Customer.objects.create(
            subscriber=user,
            stripe_id="cus_xxxxxxxxxxxxxx{0}".format(12),
            livemode=False,
            account_balance=0,
            delinquent=False,
        )
        Subscription.objects.create(
            stripe_id="sub_xxxxxxxxxxxxxx{0}".format(12),
            customer=customer,
            plan=self.plan2,
            current_period_start=period_start,
            current_period_end=period_end,
            status="active",
            start=start,
            quantity=1
        )

    def test_started_during_no_records(self):
        self.assertEqual(Subscription.objects.started_during(2013, 4).count(), 0)

    def test_started_during_has_records(self):
        self.assertEqual(Subscription.objects.started_during(2013, 1).count(), 12)

    def test_canceled_during(self):
        self.assertEqual(Subscription.objects.canceled_during(2013, 4).count(), 1)

    def test_canceled_all(self):
        self.assertEqual(
            Subscription.objects.canceled().count(), 1)

    def test_active_all(self):
        self.assertEqual(Subscription.objects.active().count(), 11)

    def test_started_plan_summary(self):
        for plan in Subscription.objects.started_plan_summary_for(2013, 1):
            if plan["plan"] == self.plan:
                self.assertEqual(plan["count"], 11)
            if plan["plan"] == self.plan2:
                self.assertEqual(plan["count"], 1)

    def test_active_plan_summary(self):
        for plan in Subscription.objects.active_plan_summary():
            if plan["plan"] == self.plan:
                self.assertEqual(plan["count"], 10)
            if plan["plan"] == self.plan2:
                self.assertEqual(plan["count"], 1)

    def test_canceled_plan_summary(self):
        for plan in Subscription.objects.canceled_plan_summary_for(2013, 1):
            if plan["plan"] == self.plan:
                self.assertEqual(plan["count"], 1)
            if plan["plan"] == self.plan2:
                self.assertEqual(plan["count"], 0)

    def test_churn(self):
        self.assertEqual(
            Subscription.objects.churn(),
            decimal.Decimal("1") / decimal.Decimal("11")
        )


class TransferManagerTest(TestCase):

    def test_transfer_summary(self):
        Transfer.sync_from_stripe_data(deepcopy(FAKE_TRANSFER))
        Transfer.sync_from_stripe_data(deepcopy(FAKE_TRANSFER_II))
        Transfer.sync_from_stripe_data(deepcopy(FAKE_TRANSFER_III))

        self.assertEqual(Transfer.objects.during(2015, 8).count(), 2)

        totals = Transfer.objects.paid_totals_for(2015, 12)
        self.assertEqual(
            totals["total_amount"], decimal.Decimal("190.10")
        )


class ChargeManagerTest(TestCase):

    def setUp(self):
        customer = Customer.objects.create(
            stripe_id="cus_XXXXXXX", livemode=False,
            account_balance=0, delinquent=False
        )

        self.march_charge = Charge.objects.create(
            stripe_id="ch_XXXXMAR1",
            customer=customer,
            created=datetime.datetime(2015, 3, 31, tzinfo=timezone.utc),
            amount=0,
            amount_refunded=0,
            currency="usd",
            fee=0,
            fee_details={},
            status="pending",
        )

        self.april_charge_1 = Charge.objects.create(
            stripe_id="ch_XXXXAPR1",
            customer=customer,
            created=datetime.datetime(2015, 4, 1, tzinfo=timezone.utc),
            amount=decimal.Decimal("20.15"),
            amount_refunded=0,
            currency="usd",
            fee=decimal.Decimal("4.90"),
            fee_details={},
            status="succeeded",
            paid=True,
        )

        self.april_charge_2 = Charge.objects.create(
            stripe_id="ch_XXXXAPR2",
            customer=customer,
            created=datetime.datetime(2015, 4, 18, tzinfo=timezone.utc),
            amount=decimal.Decimal("10.35"),
            amount_refunded=decimal.Decimal("5.35"),
            currency="usd",
            fee=0,
            fee_details={},
            status="succeeded",
            paid=True,
        )

        self.april_charge_3 = Charge.objects.create(
            stripe_id="ch_XXXXAPR3",
            customer=customer,
            created=datetime.datetime(2015, 4, 30, tzinfo=timezone.utc),
            amount=decimal.Decimal("100.00"),
            amount_refunded=decimal.Decimal("80.00"),
            currency="usd",
            fee=decimal.Decimal("5.00"),
            fee_details={},
            status="pending",
            paid=False,
        )

        self.may_charge = Charge.objects.create(
            stripe_id="ch_XXXXMAY1",
            customer=customer,
            created=datetime.datetime(2015, 5, 1, tzinfo=timezone.utc),
            amount=0,
            amount_refunded=0,
            currency="usd",
            fee=0,
            fee_details={},
            status="pending",
        )

        self.november_charge = Charge.objects.create(
            stripe_id="ch_XXXXNOV1",
            customer=customer,
            created=datetime.datetime(2015, 11, 16, tzinfo=timezone.utc),
            amount=0,
            amount_refunded=0,
            currency="usd",
            fee=0,
            fee_details={},
            status="pending",
        )

        self.charge_2014 = Charge.objects.create(
            stripe_id="ch_XXXX20141",
            customer=customer,
            created=datetime.datetime(2014, 12, 31, tzinfo=timezone.utc),
            amount=0,
            amount_refunded=0,
            currency="usd",
            fee=0,
            fee_details={},
            status="pending",
        )

        self.charge_2016 = Charge.objects.create(
            stripe_id="ch_XXXX20161",
            customer=customer,
            created=datetime.datetime(2016, 1, 1, tzinfo=timezone.utc),
            amount=0,
            amount_refunded=0,
            currency="usd",
            fee=0,
            fee_details={},
            status="pending",
        )

    def test_is_during_april_2015(self):
        raw_charges = Charge.objects.during(year=2015, month=4)
        charges = [charge.stripe_id for charge in raw_charges]

        self.assertIn(self.april_charge_1.stripe_id, charges, "April charge 1 not in charges.")
        self.assertIn(self.april_charge_2.stripe_id, charges, "April charge 2 not in charges.")
        self.assertIn(self.april_charge_3.stripe_id, charges, "April charge 3 not in charges.")

        self.assertNotIn(self.march_charge.stripe_id, charges, "March charge unexpectedly in charges.")
        self.assertNotIn(self.may_charge.stripe_id, charges, "May charge unexpectedly in charges.")
        self.assertNotIn(self.november_charge.stripe_id, charges, "November charge unexpectedly in charges.")
        self.assertNotIn(self.charge_2014.stripe_id, charges, "2014 charge unexpectedly in charges.")
        self.assertNotIn(self.charge_2016.stripe_id, charges, "2016 charge unexpectedly in charges.")

    def test_get_paid_totals_for_april_2015(self):
        paid_totals = Charge.objects.paid_totals_for(year=2015, month=4)

        self.assertEqual(decimal.Decimal("30.50"), paid_totals["total_amount"], "Total amount is not correct.")
        self.assertEqual(decimal.Decimal("4.90"), paid_totals["total_fee"], "Total fees is not correct.")
        self.assertEqual(
            decimal.Decimal("5.35"),
            paid_totals["total_refunded"], "Total amount refunded is not correct."
        )
