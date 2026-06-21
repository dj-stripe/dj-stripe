"""
dj-stripe Model Manager Tests.
"""

import datetime
import decimal
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe.models import Charge, Customer, Price, Subscription, Transfer
from djstripe.utils import get_timezone_utc

from . import (
    FAKE_PLATFORM_ACCOUNT,
    FAKE_PRICE,
    FAKE_PRICE_II,
    FAKE_PRODUCT,
    FAKE_TRANSFER,
)
from .conftest import CreateAccountMixin


def _unix(*args, **kwargs):
    """Build a Unix timestamp from a datetime spec."""
    return int(
        datetime.datetime(*args, tzinfo=get_timezone_utc(), **kwargs).timestamp()
    )


def _make_subscription(*, id, customer, plan, status, start_date, canceled_at=None):
    """Create a Subscription row with stripe_data populated for ORM lookups.

    Most Subscription fields (status, start_date, canceled_at, plan, ...) live
    in stripe_data since the dj-stripe 2.10 refactor, so the manager methods
    filter via JSONField key paths.
    """
    stripe_data = {
        "id": id,
        "object": "subscription",
        "status": status,
        "start_date": start_date,
        "plan": {"id": plan.id} if plan is not None else None,
    }
    if canceled_at is not None:
        stripe_data["canceled_at"] = canceled_at
    sub = Subscription(id=id, customer=customer, stripe_data=stripe_data)
    sub.save()
    return sub


class SubscriptionManagerTest(CreateAccountMixin, TestCase):
    def setUp(self):
        with patch(
            "stripe.Product.retrieve",
            return_value=deepcopy(FAKE_PRODUCT),
            autospec=True,
        ):
            self.plan = Price.sync_from_stripe_data(FAKE_PRICE)
            self.plan2 = Price.sync_from_stripe_data(FAKE_PRICE_II)

        # 10 active subscriptions on plan, started in Jan 2013
        for i in range(10):
            user = get_user_model().objects.create_user(
                username=f"patrick{i}", email=f"patrick{i}@example.com"
            )
            customer = Customer.objects.create(
                subscriber=user, id=f"cus_xxxxxxxxxxxxxx{i}", livemode=False
            )
            _make_subscription(
                id=f"sub_xxxxxxxxxxxxxx{i}",
                customer=customer,
                plan=self.plan,
                status="active",
                start_date=_unix(2013, 1, 1, 0, 0, 1),
            )

        # 1 canceled subscription on plan, canceled in April 2013
        user = get_user_model().objects.create_user(
            username="patrick11", email="patrick11@example.com"
        )
        customer = Customer.objects.create(
            subscriber=user, id="cus_xxxxxxxxxxxxxx11", livemode=False
        )
        _make_subscription(
            id="sub_xxxxxxxxxxxxxx11",
            customer=customer,
            plan=self.plan,
            status="canceled",
            start_date=_unix(2013, 1, 1, 0, 0, 1),
            canceled_at=_unix(2013, 4, 30),
        )

        # 1 active subscription on plan2
        user = get_user_model().objects.create_user(
            username="patrick12", email="patrick12@example.com"
        )
        customer = Customer.objects.create(
            subscriber=user, id="cus_xxxxxxxxxxxxxx12", livemode=False
        )
        _make_subscription(
            id="sub_xxxxxxxxxxxxxx12",
            customer=customer,
            plan=self.plan2,
            status="active",
            start_date=_unix(2013, 1, 1, 0, 0, 1),
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

    def test_churn(self):
        self.assertEqual(
            Subscription.objects.churn(), decimal.Decimal(1) / decimal.Decimal(11)
        )

    def test_started_plan_summary(self):
        results = list(Subscription.objects.started_plan_summary_for(2013, 1))
        # 11 subscriptions on plan, 1 on plan2
        keyed = {r["stripe_data__plan__id"]: r["count"] for r in results}
        self.assertEqual(keyed.get(self.plan.id), 11)
        self.assertEqual(keyed.get(self.plan2.id), 1)

    def test_active_plan_summary(self):
        results = list(Subscription.objects.active_plan_summary())
        # 10 active on plan, 1 active on plan2 (canceled one excluded)
        keyed = {r["stripe_data__plan__id"]: r["count"] for r in results}
        self.assertEqual(keyed.get(self.plan.id), 10)
        self.assertEqual(keyed.get(self.plan2.id), 1)

    def test_canceled_plan_summary(self):
        results = list(Subscription.objects.canceled_plan_summary_for(2013, 4))
        keyed = {r["stripe_data__plan__id"]: r["count"] for r in results}
        self.assertEqual(keyed.get(self.plan.id), 1)

    def test_status_filter_does_not_raise_field_error(self):
        # Regression test for issue #2197: Subscription.status was demoted from
        # a model column to a @property over stripe_data, but the manager
        # methods kept filtering on `status` as if it were still a column,
        # raising FieldError. Each lookup should now produce a queryset
        # backed by a stripe_data JSON path, not raise.
        for method in ("active", "canceled", "trialing", "past_due", "incomplete"):
            list(getattr(Subscription.objects, method)())


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
        self.assertEqual(totals["total_amount"], 19010)


class ChargeManagerTest(TestCase):
    def setUp(self):
        customer = Customer.objects.create(id="cus_XXXXXXX", livemode=False)

        def make_charge(*, id, created, amount, amount_refunded, status, paid=False):
            stripe_data = {
                "id": id,
                "object": "charge",
                "amount_refunded": int(amount_refunded * 100)
                if isinstance(amount_refunded, decimal.Decimal)
                else amount_refunded,
                "paid": paid,
                "refunded": False,
                "disputed": False,
            }
            charge = Charge(
                id=id,
                customer=customer,
                created=created,
                amount=amount,
                currency="usd",
                status=status,
                stripe_data=stripe_data,
            )
            charge.save()
            return charge

        self.march_charge = make_charge(
            id="ch_XXXXMAR1",
            created=datetime.datetime(2015, 3, 31, tzinfo=get_timezone_utc()),
            amount=0,
            amount_refunded=0,
            status="pending",
        )
        self.april_charge_1 = make_charge(
            id="ch_XXXXAPR1",
            created=datetime.datetime(2015, 4, 1, tzinfo=get_timezone_utc()),
            amount=decimal.Decimal("20.15"),
            amount_refunded=0,
            status="succeeded",
            paid=True,
        )
        self.april_charge_2 = make_charge(
            id="ch_XXXXAPR2",
            created=datetime.datetime(2015, 4, 18, tzinfo=get_timezone_utc()),
            amount=decimal.Decimal("10.35"),
            amount_refunded=decimal.Decimal("5.35"),
            status="succeeded",
            paid=True,
        )
        self.april_charge_3 = make_charge(
            id="ch_XXXXAPR3",
            created=datetime.datetime(2015, 4, 30, tzinfo=get_timezone_utc()),
            amount=decimal.Decimal("100.00"),
            amount_refunded=decimal.Decimal("80.00"),
            status="pending",
            paid=False,
        )
        self.may_charge = make_charge(
            id="ch_XXXXMAY1",
            created=datetime.datetime(2015, 5, 1, tzinfo=get_timezone_utc()),
            amount=0,
            amount_refunded=0,
            status="pending",
        )
        self.november_charge = make_charge(
            id="ch_XXXXNOV1",
            created=datetime.datetime(2015, 11, 16, tzinfo=get_timezone_utc()),
            amount=0,
            amount_refunded=0,
            status="pending",
        )
        self.charge_2014 = make_charge(
            id="ch_XXXX20141",
            created=datetime.datetime(2014, 12, 31, tzinfo=get_timezone_utc()),
            amount=0,
            amount_refunded=0,
            status="pending",
        )
        self.charge_2016 = make_charge(
            id="ch_XXXX20161",
            created=datetime.datetime(2016, 1, 1, tzinfo=get_timezone_utc()),
            amount=0,
            amount_refunded=0,
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

    def test_is_during_december_2015_rollover(self):
        # The 2016 charge is on 2016-01-01 00:00 UTC, i.e. the start of the
        # *next* month, and so must be excluded from December by the half-open
        # [start, next_month) UTC range (which must roll the year over).
        december_charge = Charge(
            id="ch_XXXXDEC1",
            customer=Customer.objects.get(id="cus_XXXXXXX"),
            created=datetime.datetime(2015, 12, 15, tzinfo=get_timezone_utc()),
            amount=0,
            currency="usd",
            status="pending",
            stripe_data={"id": "ch_XXXXDEC1", "object": "charge"},
        )
        december_charge.save()

        charges = [charge.id for charge in Charge.objects.during(year=2015, month=12)]

        self.assertIn(december_charge.id, charges)
        self.assertNotIn(self.november_charge.id, charges)
        self.assertNotIn(self.charge_2016.id, charges)

    def test_during_is_utc_regardless_of_time_zone(self):
        # Stripe stores `created` in UTC, so `during()` must select the same
        # calendar month no matter what settings.TIME_ZONE is active.
        from django.test import override_settings

        april_utc = {charge.id for charge in Charge.objects.during(year=2015, month=4)}

        for tz in ("UTC", "America/New_York", "Asia/Tokyo"):
            with override_settings(TIME_ZONE=tz):
                april = {
                    charge.id for charge in Charge.objects.during(year=2015, month=4)
                }
                self.assertEqual(
                    april,
                    april_utc,
                    f"during() selection changed under TIME_ZONE={tz}",
                )
                # Boundary charges (00:00 UTC on month edges) stay excluded.
                self.assertNotIn(self.march_charge.id, april)
                self.assertNotIn(self.may_charge.id, april)

    def test_get_paid_totals_for_april_2015(self):
        paid_totals = Charge.objects.paid_totals_for(year=2015, month=4)

        self.assertEqual(
            decimal.Decimal("30.50"),
            paid_totals["total_amount"],
            "Total amount is not correct.",
        )
        self.assertEqual(
            535,
            paid_totals["total_refunded"],
            "Total amount refunded is not correct.",
        )
