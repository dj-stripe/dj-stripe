"""
dj-stripe SubscriptionSchedule model tests.
"""
from copy import deepcopy
from unittest.mock import patch

import stripe
from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe.enums import SubscriptionScheduleStatus
from djstripe.models import Invoice, SubscriptionSchedule
from djstripe.settings import djstripe_settings

from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_INVOICE,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PLAN,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_SCHEDULE,
    AssertStripeFksMixin,
    datetime_to_unix,
)


class SubscriptionScheduleTest(AssertStripeFksMixin, TestCase):
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
    @patch(
        "stripe.Invoice.retrieve", autospec=True, return_value=deepcopy(FAKE_INVOICE)
    )
    def setUp(
        self,
        invoice_retrieve_mock,
        product_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

        self.default_expected_blank_fks = {
            "djstripe.Customer.coupon",
            "djstripe.Customer.default_payment_method",
            "djstripe.Charge.application_fee",
            "djstripe.Charge.dispute",
            "djstripe.Charge.latest_upcominginvoice (related name)",
            "djstripe.Charge.on_behalf_of",
            "djstripe.Charge.source_transfer",
            "djstripe.Charge.transfer",
            "djstripe.PaymentIntent.on_behalf_of",
            "djstripe.PaymentIntent.payment_method",
            "djstripe.PaymentIntent.upcominginvoice (related name)",
            "djstripe.Invoice.default_payment_method",
            "djstripe.Invoice.default_source",
            "djstripe.Subscription.default_payment_method",
            "djstripe.Subscription.default_source",
            "djstripe.Subscription.pending_setup_intent",
            "djstripe.Subscription.schedule",
            "djstripe.SubscriptionSchedule.released_subscription",
        }

        # create latest invoice
        Invoice.sync_from_stripe_data(deepcopy(FAKE_INVOICE))

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_from_stripe_data(
        self,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        canceled_schedule_fake = deepcopy(FAKE_SUBSCRIPTION_SCHEDULE)
        canceled_schedule_fake["canceled_at"] = 1624553655
        canceled_schedule_fake["status"] = SubscriptionScheduleStatus.canceled

        schedule = SubscriptionSchedule.sync_from_stripe_data(canceled_schedule_fake)

        self.assert_fks(schedule, expected_blank_fks=self.default_expected_blank_fks)
        self.assertEqual(datetime_to_unix(schedule.canceled_at), 1624553655)
        self.assertEqual(schedule.subscription.id, FAKE_SUBSCRIPTION["id"])

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test___str__(
        self,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        schedule = SubscriptionSchedule.sync_from_stripe_data(
            deepcopy(FAKE_SUBSCRIPTION_SCHEDULE)
        )
        self.assertEqual(f"<id={FAKE_SUBSCRIPTION_SCHEDULE['id']}>", str(schedule))

        self.assert_fks(schedule, expected_blank_fks=self.default_expected_blank_fks)

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_update(
        self,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        schedule = SubscriptionSchedule.sync_from_stripe_data(
            deepcopy(FAKE_SUBSCRIPTION_SCHEDULE)
        )
        with patch.object(
            stripe.SubscriptionSchedule,
            "modify",
            return_value=FAKE_SUBSCRIPTION_SCHEDULE,
        ) as patched__api_update:
            schedule.update()

        patched__api_update.assert_called_once_with(
            FAKE_SUBSCRIPTION_SCHEDULE["id"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            stripe_account=schedule.djstripe_owner_account.id,
        )
