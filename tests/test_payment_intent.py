"""
dj-stripe PaymentIntent Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
import stripe
from django.test import TestCase

from djstripe.enums import PaymentIntentStatus
from djstripe.models import Account, Customer, PaymentIntent

from . import (
    FAKE_ACCOUNT,
    FAKE_CUSTOMER,
    FAKE_PAYMENT_INTENT_DESTINATION_CHARGE,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PAYMENT_METHOD_I,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


class TestStrPaymentIntent:

    #
    # Helpers
    #
    def get_fake_payment_intent_destination_charge_no_customer():
        FAKE_PAYMENT_INTENT_DESTINATION_CHARGE_NO_CUSTOMER = deepcopy(
            FAKE_PAYMENT_INTENT_DESTINATION_CHARGE
        )
        FAKE_PAYMENT_INTENT_DESTINATION_CHARGE_NO_CUSTOMER["customer"] = None
        return FAKE_PAYMENT_INTENT_DESTINATION_CHARGE_NO_CUSTOMER

    def get_fake_payment_intent_i_no_customer():
        FAKE_PAYMENT_INTENT_I_NO_CUSTOMER = deepcopy(FAKE_PAYMENT_INTENT_I)
        FAKE_PAYMENT_INTENT_I_NO_CUSTOMER["customer"] = None
        return FAKE_PAYMENT_INTENT_I_NO_CUSTOMER

    @pytest.mark.parametrize(
        "fake_intent_data, has_account, has_customer",
        [
            (FAKE_PAYMENT_INTENT_I, False, True),
            (FAKE_PAYMENT_INTENT_DESTINATION_CHARGE, True, True),
            (get_fake_payment_intent_destination_charge_no_customer(), True, False),
            (get_fake_payment_intent_i_no_customer(), False, False),
        ],
    )
    def test___str__(self, fake_intent_data, has_account, has_customer, monkeypatch):
        def mock_customer_get(*args, **kwargs):
            return deepcopy(FAKE_CUSTOMER)

        def mock_account_get(*args, **kwargs):
            data = deepcopy(FAKE_ACCOUNT)
            # Otherwise Account.api_retrieve will invoke File.api_retrieve...
            data["settings"]["branding"] = {}
            return data

        def mock_payment_method_get(*args, **kwargs):
            return deepcopy(FAKE_PAYMENT_METHOD_I)

        # monkeypatch stripe.Product.retrieve, stripe.Price.retrieve, and  stripe.PaymentMethod.retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Account, "retrieve", mock_account_get)
        monkeypatch.setattr(stripe.Customer, "retrieve", mock_customer_get)
        monkeypatch.setattr(stripe.PaymentMethod, "retrieve", mock_payment_method_get)

        pi = PaymentIntent.sync_from_stripe_data(fake_intent_data)
        account = Account.objects.filter(id=fake_intent_data["on_behalf_of"]).first()
        customer = Customer.objects.filter(id=fake_intent_data["customer"]).first()

        if has_account and has_customer:

            assert (
                f"{pi.human_readable_amount} ({PaymentIntentStatus.humanize(fake_intent_data['status'])}) "
                f"for {account} "
                f"by {customer}"
            ) == str(pi)

        elif has_account and not has_customer:

            assert (
                f"{pi.human_readable_amount} for {account}. {PaymentIntentStatus.humanize(fake_intent_data['status'])}"
            ) == str(pi)

        elif has_customer and not has_account:

            assert (
                f"{pi.human_readable_amount} by {customer}. {PaymentIntentStatus.humanize(fake_intent_data['status'])}"
            ) == str(pi)
        elif not has_customer and not has_account:
            f"{pi.human_readable_amount} ({PaymentIntentStatus.humanize(fake_intent_data['status'])})" == str(
                pi
            )


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
