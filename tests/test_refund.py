"""
dj-stripe Charge Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test.testcases import TestCase

from djstripe.models import Invoice, Refund

from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_BALANCE_TRANSACTION_REFUND,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_INVOICE,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PRODUCT,
    FAKE_REFUND,
    FAKE_SUBSCRIPTION,
    IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    AssertStripeFksMixin,
    default_account,
)


class RefundTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        self.account = default_account()
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

        self.default_expected_blank_fks = {
            "djstripe.Account.branding_logo",
            "djstripe.Account.branding_icon",
            "djstripe.Charge.dispute",
            "djstripe.Charge.latest_upcominginvoice (related name)",
            "djstripe.Charge.transfer",
            "djstripe.Customer.coupon",
            "djstripe.Customer.default_payment_method",
            "djstripe.Invoice.default_payment_method",
            "djstripe.Invoice.default_source",
            "djstripe.PaymentIntent.on_behalf_of",
            "djstripe.PaymentIntent.payment_method",
            "djstripe.PaymentIntent.upcominginvoice (related name)",
            "djstripe.Subscription.default_payment_method",
            "djstripe.Subscription.default_source",
            "djstripe.Subscription.pending_setup_intent",
            "djstripe.Refund.failure_balance_transaction",
        }

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_sync_from_stripe_data(
        self,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account
        # TODO - remove invoice sync
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        fake_refund = deepcopy(FAKE_REFUND)

        balance_transaction_retrieve_mock.return_value = deepcopy(
            FAKE_BALANCE_TRANSACTION_REFUND
        )

        refund = Refund.sync_from_stripe_data(fake_refund)

        self.assert_fks(refund, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_reason_enum(
        self,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account
        # TODO - remove invoice sync
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        balance_transaction_retrieve_mock.return_value = deepcopy(
            FAKE_BALANCE_TRANSACTION_REFUND
        )

        fake_refund = deepcopy(FAKE_REFUND)

        for reason in (
            "duplicate",
            "fraudulent",
            "requested_by_customer",
            "expired_uncaptured_charge",
        ):
            fake_refund["reason"] = reason

            refund = Refund.sync_from_stripe_data(fake_refund)

            self.assertEqual(refund.reason, reason)

            # trigger model field validation (including enum value choices check)
            refund.full_clean()

            self.assert_fks(refund, expected_blank_fks=self.default_expected_blank_fks)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_status_enum(
        self,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account
        # TODO - remove invoice sync
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

        balance_transaction_retrieve_mock.return_value = deepcopy(
            FAKE_BALANCE_TRANSACTION_REFUND
        )

        fake_refund = deepcopy(FAKE_REFUND)

        for status in (
            "pending",
            "succeeded",
            "failed",
            "canceled",
        ):
            fake_refund["status"] = status

            refund = Refund.sync_from_stripe_data(fake_refund)

            self.assertEqual(refund.status, status)

            # trigger model field validation (including enum value choices check)
            refund.full_clean()

            self.assert_fks(refund, expected_blank_fks=self.default_expected_blank_fks)
