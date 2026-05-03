"""
dj-stripe Charge Model Tests.
"""

from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test.testcases import TestCase

from djstripe.enums import ChargeStatus, LegacySourceType
from djstripe.models import Charge, DjstripePaymentMethod, Transfer

from . import (
    COMMON_BLANK_FKS,
    FAKE_BALANCE_TRANSACTION,
    FAKE_BALANCE_TRANSACTION_REFUND,
    FAKE_CHARGE,
    FAKE_CHARGE_REFUNDED,
    FAKE_CUSTOMER,
    FAKE_FILEUPLOAD_ICON,
    FAKE_FILEUPLOAD_LOGO,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_REFUND,
    FAKE_STANDARD_ACCOUNT,
    FAKE_TRANSFER,
    AssertStripeFksMixin,
    mock_stripe_world,
)
from .conftest import CreateAccountMixin

pytestmark = pytest.mark.django_db


class ChargeTest(CreateAccountMixin, AssertStripeFksMixin, TestCase):
    @classmethod
    def setUp(self):
        # create a Stripe Platform Account
        self.account = FAKE_PLATFORM_ACCOUNT.create()

        user = get_user_model().objects.create_user(
            username="testuser", email="djstripe@example.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(user)

    def _patch_default_account(self):
        """Make Account.get_default_account return self.account for Charge.sync paths."""
        return patch(
            "djstripe.models.Account.get_default_account",
            autospec=True,
            return_value=self.account,
        )

    def test___str__(self):
        charge = Charge(
            amount=50, currency="usd", id="ch_test", status=ChargeStatus.failed
        )
        charge.stripe_data = {
            "captured": False,
            "paid": False,
            "disputed": False,
            "refunded": False,
            "amount_refunded": 0,
        }
        self.assertEqual(str(charge), "$50.00 USD (Uncaptured)")

        charge.stripe_data["captured"] = True
        self.assertEqual(str(charge), "$50.00 USD (Failed)")

        charge.status = ChargeStatus.succeeded
        charge.stripe_data["disputed"] = True
        self.assertEqual(str(charge), "$50.00 USD (Disputed)")

        charge.stripe_data["disputed"] = False
        charge.stripe_data["refunded"] = True
        charge.stripe_data["amount_refunded"] = 50
        self.assertEqual(str(charge), "$50.00 USD (Refunded)")

        charge.stripe_data["refunded"] = False
        charge.stripe_data["amount_refunded"] = 0
        self.assertEqual(str(charge), "$50.00 USD (Succeeded)")

        charge.status = ChargeStatus.pending
        self.assertEqual(str(charge), "$50.00 USD (Pending)")

    def test_capture_charge(self):
        fake_charge_no_invoice = deepcopy(FAKE_CHARGE)
        fake_charge_no_invoice.update({"invoice": None})

        fake_payment_intent_no_invoice = deepcopy(FAKE_PAYMENT_INTENT_I)
        fake_payment_intent_no_invoice.update({"invoice": None})

        with (
            self._patch_default_account(),
            mock_stripe_world(PaymentIntent=fake_payment_intent_no_invoice) as mocks,
        ):
            mocks["Charge"].return_value = fake_charge_no_invoice
            charge, created = Charge._get_or_create_from_stripe_object(
                fake_charge_no_invoice
            )
            self.assertTrue(created)

            captured_charge = charge.capture()

        self.assertTrue(captured_charge.captured)
        self.assertFalse(captured_charge.fraudulent)

        self.assert_fks(
            charge,
            expected_blank_fks={
                "djstripe.Charge.invoice",
                "djstripe.Charge.latest_invoice (related name)",
                "djstripe.Invoice.charge",
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.Plan.product",
            },
        )

    def test_sync_from_stripe_data(self):
        with self._patch_default_account(), mock_stripe_world() as mocks:
            charge = Charge.sync_from_stripe_data(deepcopy(FAKE_CHARGE))

        self.assertEqual(Decimal(20), charge.amount)
        self.assertEqual(True, charge.paid)
        self.assertEqual(False, charge.refunded)
        self.assertEqual(True, charge.captured)
        self.assertEqual(False, charge.disputed)
        self.assertEqual("Subscription creation", charge.description)
        self.assertEqual(0, charge.amount_refunded)

        self.assertEqual(self.customer.default_source["id"], charge.source_id)
        self.assertEqual(charge.source.type, LegacySourceType.card)

        self.assertGreater(len(charge.receipt_url), 1)
        self.assertTrue(charge.payment_method_details["type"])

        mocks["Charge"].assert_not_called()
        mocks["BalanceTransaction"].assert_called_once()
        assert (
            mocks["BalanceTransaction"].call_args.kwargs["id"]
            == FAKE_BALANCE_TRANSACTION["id"]
        )
        self.assert_fks(charge)

    def test_sync_from_stripe_data_refunded_on_update(self):
        # First sync the charge as usual; then sync the refunded version to hit
        # the update branch instead of insert. The two syncs need different
        # BalanceTransaction fixtures.
        with self._patch_default_account(), mock_stripe_world() as mocks:
            charge = Charge.sync_from_stripe_data(deepcopy(FAKE_CHARGE))

            self.assertEqual(Decimal(20), charge.amount)
            self.assertFalse(charge.refunded)
            self.assertEqual(len(charge.refunds.all()), 0)

            mocks["BalanceTransaction"].reset_mock()
            mocks["BalanceTransaction"].return_value = deepcopy(
                FAKE_BALANCE_TRANSACTION_REFUND
            )
            charge_refunded = Charge.sync_from_stripe_data(deepcopy(FAKE_CHARGE_REFUNDED))

        self.assertEqual(charge.id, charge_refunded.id)
        self.assertEqual(Decimal(20), charge_refunded.amount)
        self.assertTrue(charge_refunded.refunded)
        self.assertEqual(int(charge_refunded.amount * 100), charge_refunded.amount_refunded)

        mocks["Charge"].assert_not_called()
        mocks["BalanceTransaction"].assert_called_once()
        assert (
            mocks["BalanceTransaction"].call_args.kwargs["id"]
            == FAKE_BALANCE_TRANSACTION_REFUND["id"]
        )

        refunds = list(charge_refunded.refunds.all())
        self.assertEqual(len(refunds), 1)
        refund = refunds[0]
        self.assertEqual(refund.id, FAKE_REFUND["id"])
        self.assertNotEqual(
            charge_refunded.balance_transaction.id, refund.balance_transaction.id
        )
        self.assertEqual(
            charge_refunded.balance_transaction.id, FAKE_BALANCE_TRANSACTION["id"]
        )
        self.assertEqual(
            refund.balance_transaction.id, FAKE_BALANCE_TRANSACTION_REFUND["id"]
        )
        self.assert_fks(charge_refunded)

    def test_sync_from_stripe_data_refunded(self):
        # Refund-on-create needs the charge BalanceTransaction first, then the
        # refund's BalanceTransaction — feed them in via side_effect.
        with (
            self._patch_default_account(),
            mock_stripe_world() as mocks,
        ):
            mocks["BalanceTransaction"].side_effect = [
                deepcopy(FAKE_BALANCE_TRANSACTION),
                deepcopy(FAKE_BALANCE_TRANSACTION_REFUND),
            ]
            charge = Charge.sync_from_stripe_data(deepcopy(FAKE_CHARGE_REFUNDED))

        self.assertEqual(Decimal(20), charge.amount)
        self.assertTrue(charge.refunded)
        self.assertEqual(int(charge.amount * 100), charge.amount_refunded)

        mocks["Charge"].assert_not_called()
        called_ids = [
            c.kwargs["id"] for c in mocks["BalanceTransaction"].call_args_list
        ]
        assert called_ids == [
            FAKE_BALANCE_TRANSACTION["id"],
            FAKE_BALANCE_TRANSACTION_REFUND["id"],
        ]

        refunds = list(charge.refunds.all())
        self.assertEqual(len(refunds), 1)
        refund = refunds[0]
        self.assertEqual(refund.id, FAKE_REFUND["id"])

        self.assertEqual(charge.balance_transaction.id, FAKE_BALANCE_TRANSACTION["id"])
        self.assertEqual(
            refund.balance_transaction.id, FAKE_BALANCE_TRANSACTION_REFUND["id"]
        )
        self.assert_fks(charge)

    def test_sync_from_stripe_data_max_amount(self):
        fake_charge = deepcopy(FAKE_CHARGE)
        # https://support.stripe.com/questions/what-is-the-maximum-amount-i-can-charge-with-stripe
        fake_charge["amount"] = 99999999

        with self._patch_default_account(), mock_stripe_world() as mocks:
            charge = Charge.sync_from_stripe_data(fake_charge)

        self.assertEqual(Decimal("999999.99"), charge.amount)
        self.assertTrue(charge.paid)
        self.assertEqual(0, charge.amount_refunded)
        mocks["Charge"].assert_not_called()
        self.assert_fks(charge)

    def test_sync_from_stripe_data_unsupported_source(self):
        fake_charge = deepcopy(FAKE_CHARGE)
        fake_charge["source"] = {"id": "test_id", "object": "unsupported"}

        with self._patch_default_account(), mock_stripe_world() as mocks:
            charge = Charge.sync_from_stripe_data(fake_charge)

        self.assertEqual("test_id", charge.source_id)
        self.assertEqual("UNSUPPORTED_test_id", charge.source.type)
        self.assertEqual(charge.source, DjstripePaymentMethod.objects.get(id="test_id"))

        mocks["Charge"].assert_not_called()
        mocks["BalanceTransaction"].assert_called_once()
        assert (
            mocks["BalanceTransaction"].call_args.kwargs["id"]
            == FAKE_BALANCE_TRANSACTION["id"]
        )
        self.assert_fks(charge)

    def test_sync_from_stripe_data_no_customer(self):
        fake_charge = deepcopy(FAKE_CHARGE)
        fake_charge.pop("customer", None)
        # remove invoice since it requires a customer
        fake_charge.pop("invoice", None)

        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)
        fake_payment_intent["invoice"] = None

        with (
            self._patch_default_account(),
            mock_stripe_world(PaymentIntent=fake_payment_intent) as mocks,
        ):
            Charge.sync_from_stripe_data(fake_charge)

        assert Charge.objects.count() == 1
        charge = Charge.objects.get()
        assert charge.customer is None

        mocks["Charge"].assert_not_called()
        mocks["BalanceTransaction"].assert_called_once()
        assert (
            mocks["BalanceTransaction"].call_args.kwargs["id"]
            == FAKE_BALANCE_TRANSACTION["id"]
        )
        self.assert_fks(
            charge,
            expected_blank_fks={
                "djstripe.Charge.customer",
                "djstripe.Charge.invoice",
                "djstripe.Charge.latest_invoice (related name)",
                "djstripe.Invoice.charge",
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.Plan.product",
            },
        )

    def test_sync_from_stripe_data_with_transfer(self):
        fake_transfer = deepcopy(FAKE_TRANSFER)
        fake_charge = deepcopy(FAKE_CHARGE)
        fake_charge["transfer"] = fake_transfer["id"]

        with (
            self._patch_default_account(),
            patch.object(Transfer, "_attach_objects_post_save_hook"),
            patch(
                "stripe.Transfer.retrieve", return_value=fake_transfer, autospec=True
            ),
            mock_stripe_world() as mocks,
        ):
            mocks["Charge"].return_value = fake_charge
            charge, created = Charge._get_or_create_from_stripe_object(
                fake_charge, current_ids={fake_charge["id"]}
            )

        self.assertTrue(created)
        self.assertIsNotNone(charge.transfer)
        self.assertEqual(fake_transfer["id"], charge.transfer)

        mocks["Charge"].assert_not_called()
        mocks["BalanceTransaction"].assert_called_once()
        assert (
            mocks["BalanceTransaction"].call_args.kwargs["id"]
            == FAKE_BALANCE_TRANSACTION["id"]
        )
        # Charge.transfer is normally a COMMON_BLANK_FK (Connect-only); this
        # test sets it, so verify it's populated rather than allowing-blank.
        self.assert_fks(
            charge,
            optional_fks=COMMON_BLANK_FKS - {"djstripe.Charge.transfer"},
        )

    def test_sync_from_stripe_data_with_destination(self):
        fake_charge = deepcopy(FAKE_CHARGE)
        fake_charge["destination"] = FAKE_STANDARD_ACCOUNT["id"]

        with (
            patch(
                "stripe.File.retrieve",
                side_effect=[
                    deepcopy(FAKE_FILEUPLOAD_ICON),
                    deepcopy(FAKE_FILEUPLOAD_LOGO),
                ],
                autospec=True,
            ),
            mock_stripe_world(Account=FAKE_STANDARD_ACCOUNT) as mocks,
        ):
            charge, created = Charge._get_or_create_from_stripe_object(
                fake_charge, current_ids={fake_charge["id"]}
            )

        self.assertTrue(created)
        mocks["Charge"].assert_not_called()
        mocks["BalanceTransaction"].assert_called_once()
        assert (
            mocks["BalanceTransaction"].call_args.kwargs["id"]
            == FAKE_BALANCE_TRANSACTION["id"]
        )
        self.assert_fks(charge)

    def test_max_size_large_charge_on_decimal_amount(self):
        """
        By contacting stripe support, some accounts will have their limit raised
        to 11 digits.
        """
        amount = 99999999999
        assert len(str(amount)) == 11

        fake_transaction = deepcopy(FAKE_BALANCE_TRANSACTION)
        fake_transaction["amount"] = amount

        fake_charge = deepcopy(FAKE_CHARGE)
        fake_charge["amount"] = amount

        with (
            self._patch_default_account(),
            mock_stripe_world(BalanceTransaction=fake_transaction) as mocks,
        ):
            charge = Charge.sync_from_stripe_data(fake_charge)

        mocks["Charge"].assert_not_called()
        self.assertTrue(bool(charge.pk))
        self.assertEqual(charge.amount, Decimal("999999999.99"))
        self.assertEqual(charge.balance_transaction.amount, 99999999999)
