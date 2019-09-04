"""
dj-stripe Session Model Tests.
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
    FAKE_SESSION_I,
    FAKE_SUBSCRIPTION,
    AssertStripeFksMixin,
)

from djstripe.models import Session


class SessionTest(AssertStripeFksMixin, TestCase):
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
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
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
        payment_intent_retrieve_mock,
        invoice_retrieve_mock,
        file_retrieve_mock,
        customer_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
        account_retrieve_mock,
    ):
        fake_payment_intent = deepcopy(FAKE_SESSION_I)

        session = Session.sync_from_stripe_data(fake_payment_intent)

        self.assert_fks(
            session,
            expected_blank_fks={
                "djstripe.Charge.dispute",
                "djstripe.Charge.transfer",
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.Session.subscription",
                "djstripe.Subscription.pending_setup_intent",
            },
        )
