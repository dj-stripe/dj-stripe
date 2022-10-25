"""
dj-stripe SetupIntent Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
import stripe
from django.test import TestCase

from djstripe.enums import SetupIntentStatus
from djstripe.models import Account, Customer, PaymentMethod, SetupIntent
from tests import (
    FAKE_CUSTOMER,
    FAKE_PAYMENT_METHOD_I,
    FAKE_SETUP_INTENT_DESTINATION_CHARGE,
    FAKE_SETUP_INTENT_I,
    FAKE_SETUP_INTENT_II,
    FAKE_STANDARD_ACCOUNT,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db
from .conftest import CreateAccountMixin


class TestStrSetupIntent:
    #
    # Helpers
    #
    def get_fake_setup_intent_destination_charge_no_customer():
        FAKE_SETUP_INTENT_DESTINATION_CHARGE_NO_CUSTOMER = deepcopy(
            FAKE_SETUP_INTENT_DESTINATION_CHARGE
        )
        FAKE_SETUP_INTENT_DESTINATION_CHARGE_NO_CUSTOMER["customer"] = None
        return FAKE_SETUP_INTENT_DESTINATION_CHARGE_NO_CUSTOMER

    @pytest.mark.parametrize(
        "fake_intent_data, has_account, has_customer",
        [
            (FAKE_SETUP_INTENT_I, False, False),
            (FAKE_SETUP_INTENT_DESTINATION_CHARGE, True, True),
            (get_fake_setup_intent_destination_charge_no_customer(), True, False),
            (FAKE_SETUP_INTENT_II, False, True),
        ],
    )
    def test___str__(self, fake_intent_data, has_account, has_customer, monkeypatch):
        def mock_customer_get(*args, **kwargs):
            return deepcopy(FAKE_CUSTOMER)

        def mock_account_get(*args, **kwargs):
            return deepcopy(FAKE_STANDARD_ACCOUNT)

        def mock_payment_method_get(*args, **kwargs):
            return deepcopy(FAKE_PAYMENT_METHOD_I)

        # monkeypatch stripe.Account.retrieve, stripe.Customer.retrieve, and  stripe.PaymentMethod.retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Account, "retrieve", mock_account_get)
        monkeypatch.setattr(stripe.Customer, "retrieve", mock_customer_get)
        monkeypatch.setattr(stripe.PaymentMethod, "retrieve", mock_payment_method_get)

        si = SetupIntent.sync_from_stripe_data(fake_intent_data)
        pm = PaymentMethod.objects.filter(id=fake_intent_data["payment_method"]).first()
        account = Account.objects.filter(id=fake_intent_data["on_behalf_of"]).first()
        customer = Customer.objects.filter(id=fake_intent_data["customer"]).first()

        if has_account and has_customer:
            assert (
                f"{pm} ({SetupIntentStatus.humanize(fake_intent_data['status'])}) "
                f"for {account} "
                f"by {customer}"
            ) == str(si)

        elif has_account and not has_customer:
            assert (
                f"{pm} for {account}. {SetupIntentStatus.humanize(fake_intent_data['status'])}"
            ) == str(si)

        elif has_customer and not has_account:
            assert (
                f"{pm} by {customer}. {SetupIntentStatus.humanize(fake_intent_data['status'])}"
            ) == str(si)

        elif not has_customer and not has_account:
            f"{pm} ({SetupIntentStatus.humanize(fake_intent_data['status'])})" == str(
                si
            )


class SetupIntentTest(CreateAccountMixin, AssertStripeFksMixin, TestCase):
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_from_stripe_data(self, customer_retrieve_mock):
        fake_payment_intent = deepcopy(FAKE_SETUP_INTENT_I)

        setup_intent = SetupIntent.sync_from_stripe_data(fake_payment_intent)

        self.assertEqual(setup_intent.payment_method_types, ["card"])

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

        for status in (
            "requires_payment_method",
            "requires_confirmation",
            "requires_action",
            "processing",
            "canceled",
            "succeeded",
        ):
            fake_setup_intent["status"] = status

            setup_intent = SetupIntent.sync_from_stripe_data(fake_setup_intent)

            # trigger model field validation (including enum value choices check)
            setup_intent.full_clean()

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_canceled_intent(self, customer_retrieve_mock):
        fake_setup_intent = deepcopy(FAKE_SETUP_INTENT_I)

        fake_setup_intent["status"] = "canceled"
        fake_setup_intent["canceled_at"] = 1567524169

        for reason in (None, "abandoned", "requested_by_customer", "duplicate"):
            fake_setup_intent["cancellation_reason"] = reason
            setup_intent = SetupIntent.sync_from_stripe_data(fake_setup_intent)

            if reason is None:
                # enums nulls are coerced to "" by StripeModel._stripe_object_to_record
                self.assertEqual(setup_intent.cancellation_reason, "")
            else:
                self.assertEqual(setup_intent.cancellation_reason, reason)

            # trigger model field validation (including enum value choices check)
            setup_intent.full_clean()
