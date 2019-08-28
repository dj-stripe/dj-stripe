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

        setup_intent = SetupIntent.sync_from_stripe_data(fake_setup_intent)

        for status in (
            "requires_payment_method",
            "requires_confirmation",
            "requires_action",
            "processing",
            "canceled",
            "succeeded",
        ):
            setup_intent.status = status
            setup_intent.full_clean()
            setup_intent.save()
