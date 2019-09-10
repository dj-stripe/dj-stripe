"""
dj-stripe SetupIntent Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase
from tests import FAKE_CUSTOMER, FAKE_SETUP_INTENT_I, AssertStripeFksMixin

from djstripe.models import SetupIntent


class SetupIntentTest(AssertStripeFksMixin, TestCase):
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_from_stripe_data(self, customer_retrieve_mock):
        fake_payment_intent = deepcopy(FAKE_SETUP_INTENT_I)

        setup_intent = SetupIntent.sync_from_stripe_data(fake_payment_intent)

        self.assertEqual(setup_intent.payment_method_types, ["card"])

        self.assert_fks(
            setup_intent,
            expected_blank_fks={
                "djstripe.SetupIntent.customer",
                "djstripe.SetupIntent.on_behalf_of",
                "djstripe.SetupIntent.payment_method",
            },
        )

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_status_enum(self, customer_retrieve_mock):
        fake_setup_intent = deepcopy(FAKE_SETUP_INTENT_I)

        for status in (
            "requires_payment_method",
            "requires_confirmation",
            "requires_action",
            "processing",
            "canceled",
            "succeeded",
        ):
            fake_setup_intent["status"] = status

            setup_intent = SetupIntent.sync_from_stripe_data(fake_setup_intent)

            # trigger model field validation (including enum value choices check)
            setup_intent.full_clean()

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_canceled_intent(self, customer_retrieve_mock):
        fake_setup_intent = deepcopy(FAKE_SETUP_INTENT_I)

        fake_setup_intent["status"] = "canceled"
        fake_setup_intent["canceled_at"] = 1567524169

        for reason in (None, "abandoned", "requested_by_customer", "duplicate"):
            fake_setup_intent["cancellation_reason"] = reason
            setup_intent = SetupIntent.sync_from_stripe_data(fake_setup_intent)

            if reason is None:
                # enums nulls are coerced to "" by StripeModel._stripe_object_to_record
                self.assertEqual(setup_intent.cancellation_reason, "")
            else:
                self.assertEqual(setup_intent.cancellation_reason, reason)

            # trigger model field validation (including enum value choices check)
            setup_intent.full_clean()
