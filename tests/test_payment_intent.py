"""
dj-stripe PaymentIntent Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase

from djstripe.models import PaymentIntent
from tests import FAKE_CUSTOMER, FAKE_PAYMENT_INTENT_I, AssertStripeFksMixin


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
                "djstripe.Customer.subscriber",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
            },
        )

        # TODO - PaymentIntent should probably sync invoice (reverse OneToOneField)
        # self.assertIsNotNone(payment_intent.invoice)

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_status_enum(self, customer_retrieve_mock):
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)

        payment_intent = PaymentIntent.sync_from_stripe_data(fake_payment_intent)

        for status in (
            "requires_payment_method",
            "requires_confirmation",
            "requires_action",
            "processing",
            "requires_capture",
            "canceled",
            "succeeded",
        ):
            payment_intent.status = status
            payment_intent.full_clean()
            payment_intent.save()
