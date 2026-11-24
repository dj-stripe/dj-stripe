import datetime

import pytest
from django.test.testcases import TestCase
from django.utils import timezone

from djstripe.models import Coupon

pytestmark = pytest.mark.django_db


def _make_coupon(id, **stripe_data):
    """Build a Coupon model whose properties read from ``stripe_data``."""
    return Coupon.objects.create(id=id, stripe_data={"id": id, **stripe_data})


class CouponTest(TestCase):
    def test___str__(self):
        coupon = _make_coupon(
            "coupon-test-amount-off-forever",
            amount_off=10,
            currency="usd",
            duration="forever",
            name="Test coupon",
        )
        self.assertEqual(str(coupon), "Test coupon")

    def test_human_readable_usd_off_forever(self):
        coupon = _make_coupon(
            "coupon-test-amount-off-forever",
            amount_off=10,
            currency="usd",
            duration="forever",
        )
        self.assertEqual(coupon.human_readable, "$10.00 USD off forever")
        self.assertEqual(str(coupon), coupon.human_readable)

    def test_human_readable_eur_off_forever(self):
        coupon = _make_coupon(
            "coupon-test-amount-off-forever",
            amount_off=10,
            currency="eur",
            duration="forever",
        )
        self.assertEqual(coupon.human_readable, "€10.00 EUR off forever")
        self.assertEqual(str(coupon), coupon.human_readable)

    def test_human_readable_percent_off_forever(self):
        coupon = _make_coupon(
            "coupon-test-percent-off-forever",
            percent_off=10.25,
            currency="usd",
            duration="forever",
        )
        self.assertEqual(coupon.human_readable, "10.25% off forever")
        self.assertEqual(str(coupon), coupon.human_readable)

    def test_human_readable_percent_off_once(self):
        coupon = _make_coupon(
            "coupon-test-percent-off-once",
            percent_off=10.25,
            currency="usd",
            duration="once",
        )
        self.assertEqual(coupon.human_readable, "10.25% off once")
        self.assertEqual(str(coupon), coupon.human_readable)

    def test_human_readable_percent_off_one_month(self):
        coupon = _make_coupon(
            "coupon-test-percent-off-1month",
            percent_off=10.25,
            currency="usd",
            duration="repeating",
            duration_in_months=1,
        )
        self.assertEqual(coupon.human_readable, "10.25% off for 1 month")
        self.assertEqual(str(coupon), coupon.human_readable)

    def test_human_readable_percent_off_three_months(self):
        coupon = _make_coupon(
            "coupon-test-percent-off-3month",
            percent_off=10.25,
            currency="usd",
            duration="repeating",
            duration_in_months=3,
        )
        self.assertEqual(coupon.human_readable, "10.25% off for 3 months")
        self.assertEqual(str(coupon), coupon.human_readable)

    def test_human_readable_integer_percent_off_forever(self):
        coupon = _make_coupon(
            "coupon-test-percent-off-forever",
            percent_off=10,
            currency="usd",
            duration="forever",
        )
        self.assertEqual(coupon.human_readable, "10% off forever")
        self.assertEqual(str(coupon), coupon.human_readable)


class CouponIsValidTest(TestCase):
    NOW = datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC)

    def _coupon(self, **stripe_data):
        return _make_coupon(
            "coupon-test-is-valid", percent_off=10, duration="forever", **stripe_data
        )

    def test_valid_without_restrictions(self):
        assert self._coupon(valid=True).is_valid(at=self.NOW)

    def test_stripe_valid_false_wins(self):
        # e.g. Stripe already marked it invalid when it was last synced.
        assert not self._coupon(valid=False).is_valid(at=self.NOW)

    def test_redeem_by(self):
        redeem_by = int(self.NOW.timestamp())
        # Stripe still reports valid=True, because no webhook fires when
        # redeem_by passes.
        coupon = self._coupon(valid=True, redeem_by=redeem_by)

        assert coupon.is_valid(at=self.NOW - datetime.timedelta(seconds=1))
        assert coupon.is_valid(at=self.NOW)
        assert not coupon.is_valid(at=self.NOW + datetime.timedelta(seconds=1))

    def test_defaults_to_now(self):
        past = int((timezone.now() - datetime.timedelta(days=1)).timestamp())
        future = int((timezone.now() + datetime.timedelta(days=1)).timestamp())

        assert not self._coupon(valid=True, redeem_by=past).is_valid()
        assert self._coupon(valid=True, redeem_by=future).is_valid()

    def test_max_redemptions(self):
        assert self._coupon(valid=True, max_redemptions=10, times_redeemed=9).is_valid(
            at=self.NOW
        )
        assert not self._coupon(
            valid=True, max_redemptions=10, times_redeemed=10
        ).is_valid(at=self.NOW)
