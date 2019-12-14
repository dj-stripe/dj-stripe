"""
dj-stripe Session Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase
from tests import (
    FAKE_CUSTOMER,
    FAKE_PAYMENT_INTENT_I,
    FAKE_SESSION_I,
    AssertStripeFksMixin,
)

from djstripe.models import Session


class SessionTest(AssertStripeFksMixin, TestCase):
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    def test_sync_from_stripe_data(
        self, payment_intent_retrieve_mock, customer_retrieve_mock
    ):
        fake_payment_intent = deepcopy(FAKE_SESSION_I)

        session = Session.sync_from_stripe_data(fake_payment_intent)

        self.assert_fks(
            session,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.PaymentIntent.upcominginvoice (related name)",
                "djstripe.Session.subscription",
            },
        )
