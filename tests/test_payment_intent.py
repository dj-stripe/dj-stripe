"""
dj-stripe PaymentIntent Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase
from tests import FAKE_CUSTOMER, FAKE_PAYMENT_INTENT_I, AssertStripeFksMixin

from djstripe.models import PaymentIntent


class PaymentIntentTest(AssertStripeFksMixin, TestCase):
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_from_stripe_data(self, customer_retrieve_mock):
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)

        payment_intent = PaymentIntent.sync_from_stripe_data(fake_payment_intent)

        self.assert_fks(
            payment_intent,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.PaymentIntent.upcominginvoice (related name)",
            },
        )

        # TODO - PaymentIntent should probably sync invoice (reverse OneToOneField)
        # self.assertIsNotNone(payment_intent.invoice)

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_status_enum(self, customer_retrieve_mock):
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)

        for status in (
            "requires_payment_method",
            "requires_confirmation",
            "requires_action",
            "processing",
            "requires_capture",
            "canceled",
            "succeeded",
        ):
            fake_payment_intent["status"] = status
            payment_intent = PaymentIntent.sync_from_stripe_data(fake_payment_intent)

            # trigger model field validation (including enum value choices check)
            payment_intent.full_clean()

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_canceled_intent(self, customer_retrieve_mock):
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)

        fake_payment_intent["status"] = "canceled"
        fake_payment_intent["canceled_at"] = 1567524169

        for reason in (
            None,
            "duplicate",
            "fraudulent",
            "requested_by_customer",
            "abandoned",
            "failed_invoice",
            "void_invoice",
            "automatic",
        ):
            fake_payment_intent["cancellation_reason"] = reason
            payment_intent = PaymentIntent.sync_from_stripe_data(fake_payment_intent)

            if reason is None:
                # enums nulls are coerced to "" by StripeModel._stripe_object_to_record
                self.assertEqual(payment_intent.cancellation_reason, "")
            else:
                self.assertEqual(payment_intent.cancellation_reason, reason)

            # trigger model field validation (including enum value choices check)
            payment_intent.full_clean()
