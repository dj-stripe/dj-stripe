"""
dj-stripe Session Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
import stripe
from django.test import TestCase

from djstripe.models import Session
from djstripe.settings import djstripe_settings
from tests import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_INVOICE,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PAYMENT_METHOD_I,
    FAKE_PRODUCT,
    FAKE_SESSION_I,
    FAKE_SUBSCRIPTION,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


class SessionTest(AssertStripeFksMixin, TestCase):
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
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    def test_sync_from_stripe_data(
        self,
        payment_intent_retrieve_mock,
        customer_retrieve_mock,
        invoice_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):

        session = Session.sync_from_stripe_data(deepcopy(FAKE_SESSION_I))

        self.assert_fks(
            session,
            expected_blank_fks={
                "djstripe.Charge.latest_upcominginvoice (related name)",
                "djstripe.Charge.application_fee",
                "djstripe.Charge.dispute",
                "djstripe.Charge.on_behalf_of",
                "djstripe.Charge.source_transfer",
                "djstripe.Charge.transfer",
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
                "djstripe.Invoice.default_payment_method",
                "djstripe.Invoice.default_source",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.PaymentIntent.upcominginvoice (related name)",
                "djstripe.Subscription.default_payment_method",
                "djstripe.Subscription.default_source",
                "djstripe.Subscription.pending_setup_intent",
                "djstripe.Subscription.schedule",
                "djstripe.Session.subscription",
            },
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
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    def test___str__(
        self,
        payment_intent_retrieve_mock,
        customer_retrieve_mock,
        invoice_retrieve_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):

        session = Session.sync_from_stripe_data(deepcopy(FAKE_SESSION_I))

        self.assertEqual(f"<id={FAKE_SESSION_I['id']}>", str(session))


class TestSession:

    key = djstripe_settings.SUBSCRIBER_CUSTOMER_KEY

    @pytest.mark.parametrize(
        "metadata",
        [
            {},
            {"key1": "val1", key: "random"},
        ],
    )
    def test__attach_objects_post_save_hook(
        self, monkeypatch, fake_user, fake_customer, metadata
    ):
        """
        Test for Checkout Session _attach_objects_post_save_hook
        """
        user = fake_user
        customer = fake_customer

        # because create_for_user method adds subscriber
        customer.subcriber = None
        customer.save()

        # update metadata
        if metadata.get(self.key, ""):
            metadata[self.key] = user.id

        fake_stripe_session = deepcopy(FAKE_SESSION_I)
        fake_stripe_session["metadata"] = metadata

        def mock_checkout_session_get(*args, **kwargs):
            """Monkeypatched stripe.Session.retrieve"""
            return fake_stripe_session

        def mock_customer_get(*args, **kwargs):
            """Monkeypatched stripe.Customer.retrieve"""
            fake_customer = deepcopy(FAKE_CUSTOMER)
            return fake_customer

        def mock_payment_intent_get(*args, **kwargs):
            """Monkeypatched stripe.PaymentIntent.retrieve"""
            fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)
            return fake_payment_intent

        def mock_invoice_get(*args, **kwargs):
            """Monkeypatched stripe.Invoice.retrieve"""
            return deepcopy(FAKE_INVOICE)

        def mock_payment_method_get(*args, **kwargs):
            """Monkeypatched stripe.PaymentMethod.retrieve"""
            fake_payment_intent = deepcopy(FAKE_PAYMENT_METHOD_I)
            return fake_payment_intent

        def mock_subscription_get(*args, **kwargs):
            """Monkeypatched stripe.Subscription.retrieve"""
            return deepcopy(FAKE_SUBSCRIPTION)

        def mock_balance_transaction_get(*args, **kwargs):
            """Monkeypatched stripe.BalanceTransaction.retrieve"""
            return deepcopy(FAKE_BALANCE_TRANSACTION)

        def mock_product_get(*args, **kwargs):
            """Monkeypatched stripe.Product.retrieve"""
            return deepcopy(FAKE_PRODUCT)

        def mock_charge_get(*args, **kwargs):
            """Monkeypatched stripe.Charge.retrieve"""
            return deepcopy(FAKE_CHARGE)

        # monkeypatch stripe.checkout.Session.retrieve, stripe.Customer.retrieve, stripe.PaymentIntent.retrieve
        monkeypatch.setattr(
            stripe.checkout.Session, "retrieve", mock_checkout_session_get
        )
        monkeypatch.setattr(stripe.Customer, "modify", mock_customer_get)
        monkeypatch.setattr(stripe.PaymentIntent, "retrieve", mock_payment_intent_get)

        # because of Reverse o2o field sync due to PaymentIntent.sync_from_stripe_data..
        monkeypatch.setattr(stripe.Invoice, "retrieve", mock_invoice_get)
        monkeypatch.setattr(stripe.PaymentMethod, "retrieve", mock_payment_method_get)
        monkeypatch.setattr(stripe.Subscription, "retrieve", mock_subscription_get)
        monkeypatch.setattr(
            stripe.BalanceTransaction, "retrieve", mock_balance_transaction_get
        )
        monkeypatch.setattr(stripe.Product, "retrieve", mock_product_get)
        monkeypatch.setattr(stripe.Charge, "retrieve", mock_charge_get)

        # Invoke the sync to invoke _attach_objects_post_save_hook()
        session = Session.sync_from_stripe_data(fake_stripe_session)

        # refresh self.customer from db
        customer.refresh_from_db()

        assert session
        assert session.customer.id == customer.id
        assert customer.subscriber == user
        if metadata.get(self.key, ""):
            assert customer.metadata == {self.key: metadata.get(self.key)}
        else:
            assert customer.metadata == {}
