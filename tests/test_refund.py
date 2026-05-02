"""
dj-stripe Refund Model Tests.
"""

from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test.testcases import TestCase

from djstripe.models import Refund

from . import (
    FAKE_BALANCE_TRANSACTION_REFUND,
    FAKE_CUSTOMER,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_REFUND,
    AssertStripeFksMixin,
    mock_stripe_world,
)
from .conftest import CreateAccountMixin


class RefundTest(CreateAccountMixin, AssertStripeFksMixin, TestCase):
    def setUp(self):
        # create a Stripe Platform Account
        self.account = FAKE_PLATFORM_ACCOUNT.create()

        user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(user)

        self.default_expected_blank_fks = {
            "djstripe.Account.branding_logo",
            "djstripe.Account.branding_icon",
            "djstripe.Charge.application_fee",
            "djstripe.Charge.dispute",
            "djstripe.Charge.latest_upcominginvoice (related name)",
            "djstripe.Charge.on_behalf_of",
            "djstripe.Charge.refund",
            "djstripe.Charge.source_transfer",
            "djstripe.Charge.transfer",
            "djstripe.Customer.coupon",
            "djstripe.Customer.default_payment_method",
            "djstripe.Invoice.default_payment_method",
            "djstripe.Invoice.default_source",
            "djstripe.PaymentIntent.on_behalf_of",
            "djstripe.PaymentIntent.payment_method",
            "djstripe.PaymentIntent.upcominginvoice (related name)",
            "djstripe.Product.default_price",
            "djstripe.Subscription.default_payment_method",
            "djstripe.Subscription.default_source",
            "djstripe.Subscription.pending_setup_intent",
            "djstripe.Subscription.schedule",
            "djstripe.Refund.failure_balance_transaction",
        }

    def _sync_refund(self, **fixture_overrides):
        """Sync a Refund using FAKE_BALANCE_TRANSACTION_REFUND for the BT."""
        fake_refund = deepcopy(FAKE_REFUND)
        fake_refund.update(fixture_overrides)
        with mock_stripe_world(BalanceTransaction=FAKE_BALANCE_TRANSACTION_REFUND):
            return Refund.sync_from_stripe_data(fake_refund)

    def test_sync_from_stripe_data(self):
        refund = self._sync_refund()
        self.assert_fks(refund, expected_blank_fks=self.default_expected_blank_fks)

    def test___str__(self):
        refund = self._sync_refund(reason="requested_by_customer")
        self.assertEqual(str(refund), "$20.00 USD (Succeeded)")
        self.assert_fks(refund, expected_blank_fks=self.default_expected_blank_fks)
