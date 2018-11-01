from copy import deepcopy

from django.test.testcases import TestCase

from djstripe.models import Coupon

from . import FAKE_COUPON


class TransferTest(TestCase):
    def test_retrieve_coupon(self):
        coupon_data = deepcopy(FAKE_COUPON)
        coupon = Coupon.sync_from_stripe_data(coupon_data)
        self.assertEqual(coupon.id, FAKE_COUPON["id"])


class HumanReadableCouponTest(TestCase):
    def test_str_name(self):
        coupon = Coupon.objects.create(
            id="coupon-test-amount-off-forever", amount_off=10, currency="usd",
            duration="forever", name="Test coupon"
        )
        self.assertEqual(str(coupon), "Test coupon")

    def test_human_readable_usd_off_forever(self):
        coupon = Coupon.objects.create(
            id="coupon-test-amount-off-forever", amount_off=10, currency="usd",
            duration="forever",
        )
        self.assertEqual(coupon.human_readable, "$10.00 USD off forever")
        self.assertEqual(str(coupon), coupon.human_readable)

    def test_human_readable_eur_off_forever(self):
        coupon = Coupon.objects.create(
            id="coupon-test-amount-off-forever", amount_off=10, currency="eur",
            duration="forever",
        )
        self.assertEqual(coupon.human_readable, "€10.00 EUR off forever")
        self.assertEqual(str(coupon), coupon.human_readable)

    def test_human_readable_percent_off_forever(self):
        coupon = Coupon.objects.create(
            id="coupon-test-percent-off-forever", percent_off=10.25, currency="usd",
            duration="forever",
        )
        self.assertEqual(coupon.human_readable, "10.25% off forever")
        self.assertEqual(str(coupon), coupon.human_readable)

    def test_human_readable_percent_off_once(self):
        coupon = Coupon.objects.create(
            id="coupon-test-percent-off-once", percent_off=10.25, currency="usd",
            duration="once",
        )
        self.assertEqual(coupon.human_readable, "10.25% off once")
        self.assertEqual(str(coupon), coupon.human_readable)

    def test_human_readable_percent_off_one_month(self):
        coupon = Coupon.objects.create(
            id="coupon-test-percent-off-1month", percent_off=10.25, currency="usd",
            duration="repeating", duration_in_months=1,
        )
        self.assertEqual(coupon.human_readable, "10.25% off for 1 month")
        self.assertEqual(str(coupon), coupon.human_readable)

    def test_human_readable_percent_off_three_months(self):
        coupon = Coupon.objects.create(
            id="coupon-test-percent-off-3month", percent_off=10.25, currency="usd",
            duration="repeating", duration_in_months=3,
        )
        self.assertEqual(coupon.human_readable, "10.25% off for 3 months")
        self.assertEqual(str(coupon), coupon.human_readable)

    def test_human_readable_integer_percent_off_forever(self):
        coupon = Coupon.objects.create(
            id="coupon-test-percent-off-forever", percent_off=10, currency="usd",
            duration="forever",
        )
        self.assertEqual(coupon.human_readable, "10% off forever")
        self.assertEqual(str(coupon), coupon.human_readable)
