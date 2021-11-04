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
    FAKE_CUSTOMER,
    FAKE_PAYMENT_INTENT_I,
    FAKE_SESSION_I,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


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

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    def test___str__(self, payment_intent_retrieve_mock, customer_retrieve_mock):
        fake_payment_intent = deepcopy(FAKE_SESSION_I)

        session = Session.sync_from_stripe_data(fake_payment_intent)

        self.assertEqual(f"<id={FAKE_SESSION_I['id']}>", str(session))

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

        def patched_checkout_session(*args, **kwargs):
            """Monkeypatched stripe.Session.retrieve"""
            return fake_stripe_session

        def patched_customer(*args, **kwargs):
            """Monkeypatched stripe.Customer.retrieve"""
            fake_customer = deepcopy(FAKE_CUSTOMER)
            return fake_customer

        def patched_payment_intent(*args, **kwargs):
            """Monkeypatched stripe.PaymentIntent.retrieve"""
            fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)
            return fake_payment_intent

        # monkeypatch stripe.checkout.Session.retrieve, stripe.Customer.retrieve, stripe.PaymentIntent.retrieve
        monkeypatch.setattr(
            stripe.checkout.Session, "retrieve", patched_checkout_session
        )
        monkeypatch.setattr(stripe.Customer, "modify", patched_customer)
        monkeypatch.setattr(stripe.PaymentIntent, "retrieve", patched_payment_intent)

        # Invoke the sync to invoke _attach_objects_post_save_hook()
        session = Session.sync_from_stripe_data(fake_stripe_session)

        # refresh self.customer from db
        customer.refresh_from_db()

        assert session.customer.id == customer.id
        assert customer.subscriber == user
        if metadata.get(self.key, ""):
            assert customer.metadata == {self.key: metadata.get(self.key)}
        else:
            assert customer.metadata == {}
