"""
dj-stripe PaymentIntent Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase
from tests import (
    FAKE_ACCOUNT,
    FAKE_BALANCE_TRANSACTION,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_FILEUPLOAD_ICON,
    FAKE_FILEUPLOAD_LOGO,
    FAKE_INVOICE,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION,
    AssertStripeFksMixin,
)

from djstripe.models import PaymentIntent


class PaymentIntentTest(AssertStripeFksMixin, TestCase):
    @patch(
        "stripe.Account.retrieve", return_value=deepcopy(FAKE_ACCOUNT), autospec=True
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.FileUpload.retrieve",
        side_effect=[deepcopy(FAKE_FILEUPLOAD_ICON), deepcopy(FAKE_FILEUPLOAD_LOGO)],
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    def test_sync_from_stripe_data(
        self,
        subscription_retrieve_mock,
        product_retrieve_mock,
        invoice_retrieve_mock,
        file_retrieve_mock,
        customer_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
        account_retrieve_mock,
    ):
        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)

        payment_intent = PaymentIntent.sync_from_stripe_data(fake_payment_intent)

        # Check this specifically, since it's an example of reverse OneToOneField sync
        self.assertIsNotNone(payment_intent.invoice)

        self.assert_fks(
            payment_intent,
            expected_blank_fks={
                "djstripe.Charge.dispute",
                "djstripe.Charge.transfer",
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.Subscription.pending_setup_intent",
            },
        )

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
