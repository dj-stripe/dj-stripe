"""
dj-stripe PromotionCode Model Tests.
"""
from copy import deepcopy

import pytest
from django.test.testcases import TestCase

from djstripe.models import PromotionCode

from . import FAKE_PROMOTION_CODE
from .conftest import CreateAccountMixin

pytestmark = pytest.mark.django_db


class TestPromotionCode(CreateAccountMixin, TestCase):
    def test_sync_from_stripe_data(self):
        # create the PromotionCode object
        promotion_code = PromotionCode.sync_from_stripe_data(
            deepcopy(FAKE_PROMOTION_CODE)
        )
        assert promotion_code.id == "promo_1MzXMjJSZQVUcJYgrdptPwvg"
        assert promotion_code.code == "test1"
        assert promotion_code.coupon["id"] == "fake-coupon-1"
        assert promotion_code.customer.id == "cus_6lsBvm5rJ0zyHc"

    def test___str__(self):
        # create the PromotionCode object
        promotion_code = PromotionCode.sync_from_stripe_data(
            deepcopy(FAKE_PROMOTION_CODE)
        )
        assert str(promotion_code) == "test1"
