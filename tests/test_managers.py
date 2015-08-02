import datetime
import decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from djstripe.models import Event, Transfer, Customer, Subscription, Charge
from tests.test_transfer import TRANSFER_CREATED_TEST_DATA, TRANSFER_CREATED_TEST_DATA2


class CustomerManagerTest(TestCase):

    def setUp(self):
        # create customers and current subscription records
        period_start = datetime.datetime(2013, 4, 1, tzinfo=timezone.utc)
        period_end = datetime.datetime(2013, 4, 30, tzinfo=timezone.utc)
        start = datetime.datetime(2013, 1, 1, 0, 0, 1)  # more realistic start
        for i in range(10):
            customer = Customer.objects.create(
                subscriber=get_user_model().objects.create_user(username="patrick{0}".format(i),
                                                              email="patrick{0}@gmail.com".format(i)),
                stripe_id="cus_xxxxxxxxxxxxxx{0}".format(i),
                card_fingerprint="YYYYYYYY",
                card_last_4="2342",
                card_kind="Visa"
            )
            Subscription.objects.create(
                stripe_id="sub_xxxxxxxxxxxxxx{0}".format(i),
                customer=customer,
                plan="test",
                current_period_start=period_start,
                current_period_end=period_end,
                amount=(500 / decimal.Decimal("100.0")),
                status="active",
                start=start,
                quantity=1
            )
        customer = Customer.objects.create(
            subscriber=get_user_model().objects.create_user(username="patrick{0}".format(11),
                                                          email="patrick{0}@gmail.com".format(11)),
            stripe_id="cus_xxxxxxxxxxxxxx{0}".format(11),
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )
        Subscription.objects.create(
            stripe_id="sub_xxxxxxxxxxxxxx{0}".format(11),
            customer=customer,
            plan="test",
            current_period_start=period_start,
            current_period_end=period_end,
            amount=(500 / decimal.Decimal("100.0")),
            status="canceled",
            canceled_at=period_end,
            start=start,
            quantity=1
        )
        customer = Customer.objects.create(
            subscriber=get_user_model().objects.create_user(username="patrick{0}".format(12),
                                                          email="patrick{0}@gmail.com".format(12)),
            stripe_id="cus_xxxxxxxxxxxxxx{0}".format(12),
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )
        Subscription.objects.create(
            stripe_id="sub_xxxxxxxxxxxxxx{0}".format(12),
            customer=customer,
            plan="test-2",
            current_period_start=period_start,
            current_period_end=period_end,
            amount=(500 / decimal.Decimal("100.0")),
            status="active",
            start=start,
            quantity=1
        )

    def test_started_during_no_records(self):
        self.assertEquals(
            Customer.objects.started_during(2013, 4).count(),
            0
        )

    def test_started_during_has_records(self):
        self.assertEquals(
            Customer.objects.started_during(2013, 1).count(),
            12
        )

    def test_canceled_during(self):
        self.assertEquals(
            Customer.objects.canceled_during(2013, 4).count(),
            1
        )

    def test_canceled_all(self):
        self.assertEquals(
            Customer.objects.canceled().count(),
            1
        )

    def test_active_all(self):
        self.assertEquals(
            Customer.objects.active().count(),
            11
        )

    def test_started_plan_summary(self):
        for plan in Customer.objects.started_plan_summary_for(2013, 1):
            if plan["subscriptions__plan"] == "test":
                self.assertEquals(plan["count"], 11)
            if plan["subscriptions__plan"] == "test-2":
                self.assertEquals(plan["count"], 1)

    def test_active_plan_summary(self):
        for plan in Customer.objects.active_plan_summary():
            if plan["subscriptions__plan"] == "test":
                self.assertEquals(plan["count"], 10)
            if plan["subscriptions__plan"] == "test-2":
                self.assertEquals(plan["count"], 1)

    def test_canceled_plan_summary(self):
        for plan in Customer.objects.canceled_plan_summary_for(2013, 1):
            if plan["subscriptions__plan"] == "test":
                self.assertEquals(plan["count"], 1)
            if plan["subscriptions__plan"] == "test-2":
                self.assertEquals(plan["count"], 0)

    def test_churn(self):
        self.assertEquals(
            Customer.objects.churn(),
            decimal.Decimal("1") / decimal.Decimal("11")
        )


class TransferManagerTest(TestCase):

    def test_transfer_summary(self):
        event = Event.objects.create(
            stripe_id=TRANSFER_CREATED_TEST_DATA["id"],
            kind="transfer.created",
            livemode=True,
            webhook_message=TRANSFER_CREATED_TEST_DATA,
            validated_message=TRANSFER_CREATED_TEST_DATA,
            valid=True
        )
        event.process()
        event = Event.objects.create(
            stripe_id=TRANSFER_CREATED_TEST_DATA2["id"],
            kind="transfer.created",
            livemode=True,
            webhook_message=TRANSFER_CREATED_TEST_DATA2,
            validated_message=TRANSFER_CREATED_TEST_DATA2,
            valid=True
        )
        event.process()
        self.assertEquals(Transfer.objects.during(2012, 9).count(), 2)
        totals = Transfer.objects.paid_totals_for(2012, 9)
        self.assertEquals(
            totals["total_amount"], decimal.Decimal("19.10")
        )
        self.assertEquals(
            totals["total_net"], decimal.Decimal("19.10")
        )
        self.assertEquals(
            totals["total_charge_fees"], decimal.Decimal("0.90")
        )
        self.assertEquals(
            totals["total_adjustment_fees"], decimal.Decimal("0")
        )
        self.assertEquals(
            totals["total_refund_fees"], decimal.Decimal("0")
        )
        self.assertEquals(
            totals["total_validation_fees"], decimal.Decimal("0")
        )


class ChargeManagerTest(TestCase):

    def setUp(self):
        customer = Customer.objects.create(stripe_id="cus_XXXXXXX")

        self.march_charge = Charge.objects.create(
            stripe_id="ch_XXXXMAR1",
            customer=customer,
            charge_created=datetime.datetime(2015, 3, 31)
        )

        self.april_charge_1 = Charge.objects.create(
            stripe_id="ch_XXXXAPR1",
            customer=customer,
            paid=True,
            amount=decimal.Decimal("20.15"),
            fee=decimal.Decimal("4.90"),
            charge_created=datetime.datetime(2015, 4, 1)
        )

        self.april_charge_2 = Charge.objects.create(
            stripe_id="ch_XXXXAPR2",
            customer=customer,
            paid=True,
            amount=decimal.Decimal("10.35"),
            amount_refunded=decimal.Decimal("5.35"),
            charge_created=datetime.datetime(2015, 4, 18)
        )

        self.april_charge_3 = Charge.objects.create(
            stripe_id="ch_XXXXAPR3",
            customer=customer,
            paid=False,
            amount=decimal.Decimal("100.00"),
            amount_refunded=decimal.Decimal("80.00"),
            fee=decimal.Decimal("5.00"),
            charge_created=datetime.datetime(2015, 4, 30)
        )

        self.may_charge = Charge.objects.create(
            stripe_id="ch_XXXXMAY1",
            customer=customer,
            charge_created=datetime.datetime(2015, 5, 1)
        )

        self.november_charge = Charge.objects.create(
            stripe_id="ch_XXXXNOV1",
            customer=customer,
            charge_created=datetime.datetime(2015, 11, 16)
        )

        self.charge_2014 = Charge.objects.create(
            stripe_id="ch_XXXX20141",
            customer=customer,
            charge_created=datetime.datetime(2014, 12, 31)
        )

        self.charge_2016 = Charge.objects.create(
            stripe_id="ch_XXXX20161",
            customer=customer,
            charge_created=datetime.datetime(2016, 1, 1)
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
        self.assertEqual(decimal.Decimal("5.35"), paid_totals["total_refunded"], "Total amount refunded is not correct.")
