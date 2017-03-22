from copy import deepcopy

from django.test.testcases import TestCase

from djstripe.models import Coupon

from tests import FAKE_COUPON


class TransferTest(TestCase):
    def test_retrieve_coupon(self):
        coupon_data = deepcopy(FAKE_COUPON)
        coupon = Coupon.sync_from_stripe_data(coupon_data)
        self.assertEquals(coupon.stripe_id, FAKE_COUPON["id"])
