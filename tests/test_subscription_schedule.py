"""
dj-stripe SubscriptionSchedule model tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe.enums import SubscriptionScheduleStatus
from djstripe.models import SubscriptionSchedule

from . import (
    FAKE_CUSTOMER_II,
    FAKE_SUBSCRIPTION_SCHEDULE,
    AssertStripeFksMixin,
    datetime_to_unix,
)


class SubscriptionScheduleTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER_II.create_for_user(self.user)

        self.default_expected_blank_fks = {
            "djstripe.Customer.coupon",
            "djstripe.Customer.default_payment_method",
            "djstripe.SubscriptionSchedule.released_subscription",
        }

    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    def test_sync_from_stripe_data(self, customer_retrieve_mock):
        canceled_schedule_fake = deepcopy(FAKE_SUBSCRIPTION_SCHEDULE)
        canceled_schedule_fake["canceled_at"] = 1624553655
        canceled_schedule_fake["status"] = SubscriptionScheduleStatus.canceled

        schedule = SubscriptionSchedule.sync_from_stripe_data(canceled_schedule_fake)

        self.assert_fks(schedule, expected_blank_fks=self.default_expected_blank_fks)
        self.assertEqual(datetime_to_unix(schedule.canceled_at), 1624553655)
