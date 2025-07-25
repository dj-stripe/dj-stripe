"""
dj-stripe Model Manager Tests.
"""

import datetime
import decimal
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe.models import Charge, Customer, Plan, Subscription, Transfer
from djstripe.utils import get_timezone_utc

from . import (
    FAKE_PLAN,
    FAKE_PLAN_II,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_PRODUCT,
    FAKE_TRANSFER,
)
from .conftest import CreateAccountMixin


class SubscriptionManagerTest(CreateAccountMixin, TestCase):
    def setUp(self):
        # create customers and current subscription records
        period_start = datetime.datetime(2013, 4, 1, tzinfo=get_timezone_utc())
        period_end = datetime.datetime(2013, 4, 30, tzinfo=get_timezone_utc())
        start = datetime.datetime(
            2013, 1, 1, 0, 0, 1, tzinfo=get_timezone_utc()
        )  # more realistic start

        with patch(
            "stripe.Product.retrieve",
            return_value=deepcopy(FAKE_PRODUCT),
            autospec=True,
        ):
            self.plan = Plan.sync_from_stripe_data(FAKE_PLAN)
            self.plan2 = Plan.sync_from_stripe_data(FAKE_PLAN_II)

        for i in range(10):
            user = get_user_model().objects.create_user(
                username=f"patrick{i}",
                email=f"patrick{i}@example.com",
            )
            customer = Customer.objects.create(
                subscriber=user,
                id=f"cus_xxxxxxxxxxxxxx{i}",
                livemode=False,
            )

            Subscription.objects.create(
                id=f"sub_xxxxxxxxxxxxxx{i}",
                customer=customer,
                plan=self.plan,
                current_period_start=period_start,
                current_period_end=period_end,
                status="active",
                start_date=start,
                quantity=1,
            )

        user = get_user_model().objects.create_user(
            username="patrick11", email="patrick11@example.com"
        )
        customer = Customer.objects.create(
            subscriber=user, id="cus_xxxxxxxxxxxxxx11", livemode=False
        )
        Subscription.objects.create(
            id="sub_xxxxxxxxxxxxxx11",
            customer=customer,
            plan=self.plan,
            current_period_start=period_start,
            current_period_end=period_end,
            status="canceled",
            canceled_at=period_end,
            start_date=start,
            quantity=1,
        )

        user = get_user_model().objects.create_user(
            username="patrick12", email="patrick12@example.com"
        )
        customer = Customer.objects.create(
            subscriber=user, id="cus_xxxxxxxxxxxxxx12", livemode=False
        )
        Subscription.objects.create(
            id="sub_xxxxxxxxxxxxxx12",
            customer=customer,
            plan=self.plan2,
            current_period_start=period_start,
            current_period_end=period_end,
            status="active",
            start_date=start,
            quantity=1,
        )

    def test_started_during_no_records(self):
        self.assertEqual(Subscription.objects.started_during(2013, 4).count(), 0)

    def test_started_during_has_records(self):
        self.assertEqual(Subscription.objects.started_during(2013, 1).count(), 12)

    def test_canceled_during(self):
        self.assertEqual(Subscription.objects.canceled_during(2013, 4).count(), 1)

    def test_canceled_all(self):
        self.assertEqual(Subscription.objects.canceled().count(), 1)

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
            Subscription.objects.churn(), decimal.Decimal(1) / decimal.Decimal(11)
        )


class TransferManagerTest(TestCase):
    @patch.object(Transfer, "_attach_objects_post_save_hook")
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_PLATFORM_ACCOUNT),
    )
    def test_transfer_summary(
        self, account_retrieve_mock, transfer__attach_object_post_save_hook_mock
    ):
        def FAKE_TRANSFER_III():
            data = deepcopy(FAKE_TRANSFER)
            data["id"] = "tr_17O4U52eZvKYlo2CmyYbDAEy"
            data["amount"] = 19010
            data["created"] = 1451560845
            return data

        def FAKE_TRANSFER_II():
            data = deepcopy(FAKE_TRANSFER)
            data["id"] = "tr_16hTzv2eZvKYlo2CWuyMmuvV"
            data["amount"] = 2000
            data["created"] = 1440420000
            return data

        Transfer.sync_from_stripe_data(deepcopy(FAKE_TRANSFER))
        Transfer.sync_from_stripe_data(FAKE_TRANSFER_II())
        Transfer.sync_from_stripe_data(FAKE_TRANSFER_III())

        self.assertEqual(Transfer.objects.during(2015, 8).count(), 2)

        totals = Transfer.objects.paid_totals_for(2015, 12)
        self.assertEqual(totals["total_amount"], decimal.Decimal("190.10"))


class ChargeManagerTest(TestCase):
    def setUp(self):
        customer = Customer.objects.create(id="cus_XXXXXXX", livemode=False)

        self.march_charge = Charge.objects.create(
            id="ch_XXXXMAR1",
            customer=customer,
            created=datetime.datetime(2015, 3, 31, tzinfo=get_timezone_utc()),
            amount=0,
            amount_refunded=0,
            currency="usd",
            status="pending",
        )

        self.april_charge_1 = Charge.objects.create(
            id="ch_XXXXAPR1",
            customer=customer,
            created=datetime.datetime(2015, 4, 1, tzinfo=get_timezone_utc()),
            amount=decimal.Decimal("20.15"),
            amount_refunded=0,
            currency="usd",
            status="succeeded",
            paid=True,
        )

        self.april_charge_2 = Charge.objects.create(
            id="ch_XXXXAPR2",
            customer=customer,
            created=datetime.datetime(2015, 4, 18, tzinfo=get_timezone_utc()),
            amount=decimal.Decimal("10.35"),
            amount_refunded=decimal.Decimal("5.35"),
            currency="usd",
            status="succeeded",
            paid=True,
        )

        self.april_charge_3 = Charge.objects.create(
            id="ch_XXXXAPR3",
            customer=customer,
            created=datetime.datetime(2015, 4, 30, tzinfo=get_timezone_utc()),
            amount=decimal.Decimal("100.00"),
            amount_refunded=decimal.Decimal("80.00"),
            currency="usd",
            status="pending",
            paid=False,
        )

        self.may_charge = Charge.objects.create(
            id="ch_XXXXMAY1",
            customer=customer,
            created=datetime.datetime(2015, 5, 1, tzinfo=get_timezone_utc()),
            amount=0,
            amount_refunded=0,
            currency="usd",
            status="pending",
        )

        self.november_charge = Charge.objects.create(
            id="ch_XXXXNOV1",
            customer=customer,
            created=datetime.datetime(2015, 11, 16, tzinfo=get_timezone_utc()),
            amount=0,
            amount_refunded=0,
            currency="usd",
            status="pending",
        )

        self.charge_2014 = Charge.objects.create(
            id="ch_XXXX20141",
            customer=customer,
            created=datetime.datetime(2014, 12, 31, tzinfo=get_timezone_utc()),
            amount=0,
            amount_refunded=0,
            currency="usd",
            status="pending",
        )

        self.charge_2016 = Charge.objects.create(
            id="ch_XXXX20161",
            customer=customer,
            created=datetime.datetime(2016, 1, 1, tzinfo=get_timezone_utc()),
            amount=0,
            amount_refunded=0,
            currency="usd",
            status="pending",
        )

    def test_is_during_april_2015(self):
        raw_charges = Charge.objects.during(year=2015, month=4)
        charges = [charge.id for charge in raw_charges]

        self.assertIn(self.april_charge_1.id, charges, "April charge 1 not in charges.")
        self.assertIn(self.april_charge_2.id, charges, "April charge 2 not in charges.")
        self.assertIn(self.april_charge_3.id, charges, "April charge 3 not in charges.")

        self.assertNotIn(
            self.march_charge.id, charges, "March charge unexpectedly in charges."
        )
        self.assertNotIn(
            self.may_charge.id, charges, "May charge unexpectedly in charges."
        )
        self.assertNotIn(
            self.november_charge.id, charges, "November charge unexpectedly in charges."
        )
        self.assertNotIn(
            self.charge_2014.id, charges, "2014 charge unexpectedly in charges."
        )
        self.assertNotIn(
            self.charge_2016.id, charges, "2016 charge unexpectedly in charges."
        )

    def test_get_paid_totals_for_april_2015(self):
        paid_totals = Charge.objects.paid_totals_for(year=2015, month=4)

        self.assertEqual(
            decimal.Decimal("30.50"),
            paid_totals["total_amount"],
            "Total amount is not correct.",
        )
        self.assertEqual(
            decimal.Decimal("5.35"),
            paid_totals["total_refunded"],
            "Total amount refunded is not correct.",
        )
