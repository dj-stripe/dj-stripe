import datetime
from unittest.mock import patch

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

    # --- valid property tests (issue #717) ---

    def test_valid_no_restrictions(self):
        """A coupon with no redeem_by or max_redemptions is always valid."""
        coupon = _make_coupon(
            "coupon-test-valid",
            percent_off=10,
            currency="usd",
            duration="forever",
        )
        self.assertTrue(coupon.valid)

    def test_valid_future_redeem_by(self):
        """A coupon with a future redeem_by date is valid."""
        future_ts = int((timezone.now() + datetime.timedelta(days=30)).timestamp())
        coupon = _make_coupon(
            "coupon-test-future-redeem-by",
            percent_off=10,
            currency="usd",
            duration="forever",
            redeem_by=future_ts,
        )
        self.assertTrue(coupon.valid)

    def test_valid_redeem_by_is_now(self):
        """A coupon whose redeem_by equals the current time is valid.

        Uses ``<`` (strict less-than), so a coupon expiring exactly now
        is still considered valid.
        """
        now = timezone.now().replace(microsecond=0)
        now_ts = int(now.timestamp())
        coupon = _make_coupon(
            "coupon-test-redeem-by-now",
            percent_off=10,
            currency="usd",
            duration="forever",
            redeem_by=now_ts,
        )
        with patch("djstripe.models.billing.timezone.now", return_value=now):
            self.assertTrue(coupon.valid)

    def test_valid_past_redeem_by(self):
        """A coupon with a past redeem_by date is invalid (expired)."""
        past_ts = int((timezone.now() - datetime.timedelta(days=1)).timestamp())
        coupon = _make_coupon(
            "coupon-test-past-redeem-by",
            percent_off=10,
            currency="usd",
            duration="forever",
            redeem_by=past_ts,
        )
        self.assertFalse(coupon.valid)

    def test_valid_max_redemptions_not_reached(self):
        """A coupon that hasn't reached max_redemptions is valid."""
        coupon = _make_coupon(
            "coupon-test-max-redemptions-active",
            percent_off=10,
            currency="usd",
            duration="forever",
            max_redemptions=100,
            times_redeemed=50,
        )
        self.assertTrue(coupon.valid)

    def test_valid_max_redemptions_reached(self):
        """A coupon that has reached max_redemptions is invalid (exhausted)."""
        coupon = _make_coupon(
            "coupon-test-max-redemptions-exhausted",
            percent_off=10,
            currency="usd",
            duration="forever",
            max_redemptions=100,
            times_redeemed=100,
        )
        self.assertFalse(coupon.valid)

    def test_valid_both_expired_and_exhausted(self):
        """When both redeem_by and max_redemptions indicate invalid, the
        coupon is invalid."""
        past_ts = int((timezone.now() - datetime.timedelta(days=1)).timestamp())
        coupon = _make_coupon(
            "coupon-test-both-invalid",
            percent_off=10,
            currency="usd",
            duration="forever",
            redeem_by=past_ts,
            max_redemptions=10,
            times_redeemed=10,
        )
        self.assertFalse(coupon.valid)
