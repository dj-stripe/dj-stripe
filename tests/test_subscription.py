"""
dj-stripe Subscription Model Tests.
"""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from unittest.mock import PropertyMock, patch

import pytest
import stripe
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from stripe.error import InvalidRequestError

from djstripe.enums import SubscriptionStatus
from djstripe.models import Plan, Product, Subscription
from djstripe.models.billing import Invoice
from djstripe.settings import djstripe_settings

from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_CARD,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CHARGE,
    FAKE_CHARGE_II,
    FAKE_CUSTOMER,
    FAKE_CUSTOMER_II,
    FAKE_INVOICE,
    FAKE_INVOICE_II,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PAYMENT_INTENT_II,
    FAKE_PAYMENT_METHOD_II,
    FAKE_PLAN,
    FAKE_PLAN_II,
    FAKE_PLAN_METERED,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_CANCELED,
    FAKE_SUBSCRIPTION_II,
    FAKE_SUBSCRIPTION_III,
    FAKE_SUBSCRIPTION_METERED,
    FAKE_SUBSCRIPTION_MULTI_PLAN,
    FAKE_SUBSCRIPTION_NOT_PERIOD_CURRENT,
    FAKE_TAX_RATE_EXAMPLE_1_VAT,
    AssertStripeFksMixin,
    datetime_to_unix,
)

pytestmark = pytest.mark.django_db

# TODO: test with Prices instead of Plans when creating Subscriptions
# with Prices is fully supported


class SubscriptionStrTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER_II.create_for_user(self.user)

    @patch("djstripe.models.billing.Subscription._api_create", autospec=True)
    @patch(
        "stripe.Plan.retrieve",
        side_effect=[deepcopy(FAKE_PLAN), deepcopy(FAKE_PLAN_II)],
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    def test___str__(
        self,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        subscription_creation_mock,
    ):
        assert self.customer
        subscription_fake_1 = deepcopy(FAKE_SUBSCRIPTION_III)
        subscription_fake_1["current_period_end"] += int(
            datetime.timestamp(timezone.now())
        )
        subscription_fake_1["latest_invoice"] = None

        subscription_fake_2 = deepcopy(FAKE_SUBSCRIPTION_II)
        subscription_fake_2["current_period_end"] += int(
            datetime.timestamp(timezone.now())
        )
        subscription_fake_2["customer"] = self.customer.id
        subscription_fake_2["latest_invoice"] = None

        subscription_creation_mock.side_effect = [
            subscription_fake_1,
            subscription_fake_2,
        ]

        # sync subscriptions (to update the changes just made)
        Subscription.sync_from_stripe_data(subscription_fake_1)
        Subscription.sync_from_stripe_data(subscription_fake_2)

        # refresh self.customer from db
        self.customer.refresh_from_db()

        # subscribe the customer to 2 plans
        self.customer.subscribe(plan=FAKE_PLAN["id"])
        self.customer.subscribe(plan=FAKE_PLAN_II["id"])

        subscriptions_lst = self.customer._get_valid_subscriptions()
        products_lst = [
            subscription.plan.product.name
            for subscription in subscriptions_lst
            if subscription and subscription.plan
        ]

        self.assertEqual(
            str(Subscription.objects.get(id=subscription_fake_2["id"])),
            f"{self.customer} on {' and '.join(products_lst)}",
        )


class SubscriptionTest(AssertStripeFksMixin, TestCase):
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
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["pause_collection"] = {
            "behavior": "keep_as_draft",
            "resumes_at": 1624553615,
        }
        subscription_fake["cancel_at"] = 1624553655

        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        assert subscription

        self.assertEqual(subscription.default_tax_rates.count(), 1)
        self.assertEqual(
            subscription.default_tax_rates.first().id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )
        self.assertEqual(datetime_to_unix(subscription.cancel_at), 1624553655)
        self.assertEqual(
            subscription.pause_collection,
            subscription_fake["pause_collection"],
        )

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_from_stripe_data_default_source_string(
        self, customer_retrieve_mock, product_retrieve_mock, plan_retrieve_mock
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["default_source"] = FAKE_CARD["id"]

        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        assert subscription
        self.assertEqual(subscription.default_source.id, FAKE_CARD["id"])

        # pop out "djstripe.Subscription.default_source" from self.assert_fks
        expected_blank_fks = deepcopy(self.default_expected_blank_fks)
        expected_blank_fks.remove("djstripe.Subscription.default_source")
        self.assert_fks(subscription, expected_blank_fks=expected_blank_fks)

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN_II), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        autospec=True,
    )
    def test_sync_items_with_tax_rates(
        self,
        subscription_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION_II)
        subscription_fake["latest_invoice"] = FAKE_INVOICE["id"]
        subscription_retrieve_mock.return_value = subscription_fake

        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        assert subscription

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

        self.assertEqual(subscription.default_tax_rates.count(), 0)
        first_item = subscription.items.first()

        self.assertEqual(first_item.tax_rates.count(), 1)
        self.assertEqual(
            first_item.tax_rates.first().id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_is_status_temporarily_current(
        self, customer_retrieve_mock, product_retrieve_mock, plan_retrieve_mock
    ):
        product = Product.sync_from_stripe_data(deepcopy(FAKE_PRODUCT))
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        assert subscription
        subscription.canceled_at = timezone.now() + timezone.timedelta(days=7)
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=7)
        subscription.cancel_at_period_end = True
        subscription.save()

        self.assertTrue(subscription.is_status_current())
        self.assertTrue(subscription.is_status_temporarily_current())
        self.assertTrue(subscription.is_valid())
        self.assertTrue(subscription in self.customer.active_subscriptions)
        self.assertTrue(self.customer.is_subscribed_to(product))
        self.assertTrue(self.customer.has_any_active_subscription())

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_is_status_temporarily_current_false(
        self, customer_retrieve_mock, product_retrieve_mock, plan_retrieve_mock
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=7)
        subscription.save()

        self.assertTrue(subscription.is_status_current())
        self.assertFalse(subscription.is_status_temporarily_current())
        self.assertTrue(subscription.is_valid())
        self.assertTrue(subscription in self.customer.active_subscriptions)
        self.assertTrue(self.customer.is_subscribed_to(FAKE_PRODUCT["id"]))
        self.assertTrue(self.customer.has_any_active_subscription())

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_is_status_temporarily_current_false_and_canceled(
        self, customer_retrieve_mock, product_retrieve_mock, plan_retrieve_mock
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        assert subscription
        subscription.status = SubscriptionStatus.canceled
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=7)
        subscription.save()

        self.assertFalse(subscription.is_status_current())
        self.assertFalse(subscription.is_status_temporarily_current())
        self.assertFalse(subscription.is_valid())
        self.assertFalse(subscription in self.customer.active_subscriptions)
        self.assertFalse(self.customer.is_subscribed_to(FAKE_PRODUCT["id"]))
        self.assertFalse(self.customer.has_any_active_subscription())

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.modify",
        autospec=True,
    )
    @patch("stripe.Subscription.retrieve", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_extend(
        self,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        subscription_modify_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        current_period_end = timezone.now() - timezone.timedelta(days=20)
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["current_period_end"] = int(current_period_end.timestamp())
        subscription_retrieve_mock.return_value = subscription_fake

        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        self.assertFalse(subscription in self.customer.active_subscriptions)
        self.assertEqual(self.customer.active_subscriptions.count(), 0)

        # Extend the Subscription by 30 days
        delta = timezone.timedelta(days=30)
        subscription_updated = deepcopy(subscription_fake)
        subscription_updated["trial_end"] = int(
            (current_period_end + delta).timestamp()
        )
        subscription_modify_mock.return_value = subscription_updated

        extended_subscription = subscription.extend(delta)
        product = Product.sync_from_stripe_data(deepcopy(FAKE_PRODUCT))

        self.assertNotEqual(None, extended_subscription.trial_end)
        self.assertTrue(self.customer.is_subscribed_to(product))
        self.assertTrue(self.customer.has_any_active_subscription())

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_extend_negative_delta(
        self,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION_NOT_PERIOD_CURRENT)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        with self.assertRaises(ValueError):
            subscription.extend(timezone.timedelta(days=-30))

        self.assertFalse(self.customer.is_subscribed_to(FAKE_PRODUCT["id"]))
        self.assertFalse(self.customer.has_any_active_subscription())

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.modify",
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_extend_with_trial(
        self,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        subscription_modify_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        trial_end = timezone.now() + timezone.timedelta(days=5)
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.trial_end = trial_end
        subscription.save()

        # Extend the Subscription by 30 days
        delta = timezone.timedelta(days=30)
        subscription_updated = deepcopy(subscription_fake)
        subscription_updated["trial_end"] = int((trial_end + delta).timestamp())
        subscription_modify_mock.return_value = subscription_updated

        extended_subscription = subscription.extend(delta)

        new_trial_end = subscription.trial_end + delta
        self.assertEqual(
            new_trial_end.replace(microsecond=0), extended_subscription.trial_end
        )
        self.assertTrue(self.customer.is_subscribed_to(FAKE_PRODUCT["id"]))
        self.assertTrue(self.customer.has_any_active_subscription())

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.modify",
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_update(
        self,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        subscription_modify_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        self.assertEqual(1, subscription.quantity)

        # Update the quantity of the Subscription
        subscription_updated = deepcopy(FAKE_SUBSCRIPTION)
        subscription_updated["quantity"] = 4
        subscription_modify_mock.return_value = subscription_updated

        new_subscription = subscription.update(quantity=4)

        self.assertEqual(4, new_subscription.quantity)

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.modify",
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_update_deprecation_warnings_raised(
        self,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        subscription_modify_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        assert subscription

        self.assertEqual(1, subscription.quantity)

        # prorate the Subscription
        subscription_updated = deepcopy(FAKE_SUBSCRIPTION)
        subscription_updated["prorate"] = True
        subscription_modify_mock.return_value = subscription_updated

        with pytest.warns(DeprecationWarning, match=r"The `prorate` parameter to"):
            subscription.update(prorate=True)

        # prorate the Subscription
        subscription_updated = deepcopy(FAKE_SUBSCRIPTION)
        subscription_updated["subscription_prorate"] = True
        subscription_modify_mock.return_value = subscription_updated

        with pytest.warns(
            DeprecationWarning, match=r"The `subscription_prorate` parameter to"
        ):
            subscription.update(subscription_prorate=True)

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.modify",
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_update_with_plan_model(
        self,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        subscription_modify_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        new_plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN_II))

        self.assertEqual(FAKE_PLAN["id"], subscription.plan.id)

        # Update the Subscription's plan
        subscription_updated = deepcopy(FAKE_SUBSCRIPTION)
        subscription_updated["plan"] = deepcopy(FAKE_PLAN_II)
        subscription_modify_mock.return_value = subscription_updated

        new_subscription = subscription.update(plan=new_plan)

        self.assertEqual(FAKE_PLAN_II["id"], new_subscription.plan.id)

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

        self.assert_fks(new_plan, expected_blank_fks={})

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch("stripe.Subscription.delete", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_cancel_now(
        self,
        customer_retrieve_mock,
        subscription_delete_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=7)
        subscription.save()

        cancel_timestamp = datetime_to_unix(timezone.now())
        canceled_subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        canceled_subscription_fake["status"] = SubscriptionStatus.canceled
        canceled_subscription_fake["canceled_at"] = cancel_timestamp
        canceled_subscription_fake["ended_at"] = cancel_timestamp

        subscription_delete_mock.return_value = canceled_subscription_fake

        self.assertTrue(self.customer.is_subscribed_to(FAKE_PRODUCT["id"]))
        self.assertEqual(self.customer.active_subscriptions.count(), 1)
        self.assertTrue(self.customer.has_any_active_subscription())

        new_subscription = subscription.cancel(at_period_end=False)

        self.assertEqual(SubscriptionStatus.canceled, new_subscription.status)
        self.assertEqual(False, new_subscription.cancel_at_period_end)
        self.assertEqual(new_subscription.canceled_at, new_subscription.ended_at)
        self.assertFalse(new_subscription.is_valid())
        self.assertFalse(new_subscription.is_status_temporarily_current())
        self.assertFalse(new_subscription in self.customer.active_subscriptions)
        self.assertFalse(self.customer.is_subscribed_to(FAKE_PRODUCT["id"]))
        self.assertFalse(self.customer.has_any_active_subscription())

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.modify",
        autospec=True,
    )
    @patch("stripe.Subscription.delete", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_cancel_at_period_end(
        self,
        customer_retrieve_mock,
        subscription_delete_mock,
        subscription_modify_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        current_period_end = timezone.now() + timezone.timedelta(days=7)

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.current_period_end = current_period_end
        subscription.save()

        canceled_subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        canceled_subscription_fake["current_period_end"] = datetime_to_unix(
            current_period_end
        )
        canceled_subscription_fake["canceled_at"] = datetime_to_unix(timezone.now())
        subscription_delete_mock.return_value = (
            canceled_subscription_fake  # retrieve().delete()
        )

        self.assertTrue(self.customer.is_subscribed_to(FAKE_PRODUCT["id"]))
        self.assertTrue(self.customer.has_any_active_subscription())
        self.assertEqual(self.customer.active_subscriptions.count(), 1)
        self.assertTrue(subscription in self.customer.active_subscriptions)

        # Update the Subscription by cancelling it at the end of the period
        subscription_updated = deepcopy(canceled_subscription_fake)
        subscription_updated["cancel_at_period_end"] = True
        subscription_modify_mock.return_value = subscription_updated

        new_subscription = subscription.cancel(at_period_end=True)

        self.assertEqual(self.customer.active_subscriptions.count(), 1)
        self.assertTrue(new_subscription in self.customer.active_subscriptions)

        self.assertEqual(SubscriptionStatus.active, new_subscription.status)
        self.assertEqual(True, new_subscription.cancel_at_period_end)
        self.assertNotEqual(new_subscription.canceled_at, new_subscription.ended_at)
        self.assertTrue(new_subscription.is_valid())
        self.assertTrue(new_subscription.is_status_temporarily_current())
        self.assertTrue(self.customer.is_subscribed_to(FAKE_PRODUCT["id"]))
        self.assertTrue(self.customer.has_any_active_subscription())

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch("stripe.Subscription.delete", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_cancel_during_trial_sets_at_period_end(
        self,
        customer_retrieve_mock,
        subscription_delete_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.trial_end = timezone.now() + timezone.timedelta(days=7)
        subscription.save()

        cancel_timestamp = datetime_to_unix(timezone.now())
        canceled_subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        canceled_subscription_fake["status"] = SubscriptionStatus.canceled
        canceled_subscription_fake["canceled_at"] = cancel_timestamp
        canceled_subscription_fake["ended_at"] = cancel_timestamp
        subscription_delete_mock.return_value = canceled_subscription_fake

        self.assertTrue(self.customer.is_subscribed_to(FAKE_PRODUCT["id"]))
        self.assertTrue(self.customer.has_any_active_subscription())

        new_subscription = subscription.cancel(at_period_end=False)

        self.assertEqual(SubscriptionStatus.canceled, new_subscription.status)
        self.assertEqual(False, new_subscription.cancel_at_period_end)
        self.assertEqual(new_subscription.canceled_at, new_subscription.ended_at)
        self.assertFalse(new_subscription.is_valid())
        self.assertFalse(self.customer.is_subscribed_to(FAKE_PRODUCT["id"]))
        self.assertFalse(self.customer.has_any_active_subscription())

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.modify",
        autospec=True,
    )
    @patch("stripe.Subscription.retrieve", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_cancel_and_reactivate(
        self,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        subscription_modify_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        current_period_end = timezone.now() + timezone.timedelta(days=7)

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        assert subscription
        subscription.current_period_end = current_period_end
        subscription.save()

        canceled_subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        canceled_subscription_fake["current_period_end"] = datetime_to_unix(
            current_period_end
        )
        canceled_subscription_fake["canceled_at"] = datetime_to_unix(timezone.now())
        subscription_retrieve_mock.return_value = canceled_subscription_fake

        self.assertTrue(self.customer.is_subscribed_to(FAKE_PRODUCT["id"]))
        self.assertTrue(self.customer.has_any_active_subscription())

        # Update the Subscription by cancelling it at the end of the period
        subscription_updated = deepcopy(canceled_subscription_fake)
        subscription_updated["cancel_at_period_end"] = True
        subscription_modify_mock.return_value = subscription_updated

        new_subscription = subscription.cancel(at_period_end=True)
        self.assertEqual(new_subscription.cancel_at_period_end, True)

        new_subscription.reactivate()
        subscription_reactivate_fake = deepcopy(FAKE_SUBSCRIPTION)
        reactivated_subscription = Subscription.sync_from_stripe_data(
            subscription_reactivate_fake
        )
        self.assertEqual(reactivated_subscription.cancel_at_period_end, False)

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch("djstripe.models.Subscription._api_delete", autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_CANCELED),
    )
    def test_cancel_already_canceled(
        self,
        subscription_retrieve_mock,
        product_retrieve_mock,
        subscription_delete_mock,
    ):
        subscription_delete_mock.side_effect = InvalidRequestError(
            "No such subscription: sub_xxxx", "blah"
        )

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        self.assertEqual(Subscription.objects.filter(status="canceled").count(), 0)
        subscription.cancel(at_period_end=False)
        self.assertEqual(Subscription.objects.filter(status="canceled").count(), 1)

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch("djstripe.models.Subscription._api_delete", autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_cancel_error_in_cancel(
        self, product_retrieve_mock, subscription_delete_mock
    ):
        subscription_delete_mock.side_effect = InvalidRequestError(
            "Unexpected error", "blah"
        )

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        with self.assertRaises(InvalidRequestError):
            subscription.cancel(at_period_end=False)

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )

    @patch("stripe.Plan.retrieve", autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        autospec=True,
    )
    def test_sync_multi_plan(
        self,
        subscription_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION_MULTI_PLAN)
        subscription_fake["latest_invoice"] = FAKE_INVOICE["id"]
        subscription_retrieve_mock.return_value = subscription_fake

        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        self.assertIsNone(subscription.plan)
        self.assertIsNone(subscription.quantity)

        items = subscription.items.all()
        self.assertEqual(2, len(items))

        # delete pydanny customer as that causes issues with Invoice and Latest_invoice FKs
        self.customer.delete()

        self.assert_fks(
            subscription,
            expected_blank_fks=(
                self.default_expected_blank_fks
                | {
                    "djstripe.Customer.subscriber",
                    "djstripe.Subscription.plan",
                    "djstripe.Charge.latest_upcominginvoice (related name)",
                    "djstripe.Charge.application_fee",
                    "djstripe.Charge.dispute",
                    "djstripe.Charge.on_behalf_of",
                    "djstripe.Charge.source_transfer",
                    "djstripe.Charge.transfer",
                    "djstripe.PaymentIntent.upcominginvoice (related name)",
                    "djstripe.PaymentIntent.on_behalf_of",
                    "djstripe.PaymentIntent.payment_method",
                    "djstripe.Invoice.default_payment_method",
                    "djstripe.Invoice.default_source",
                    "djstripe.Invoice.charge",
                    "djstripe.Invoice.customer",
                    "djstripe.Invoice.payment_intent",
                    "djstripe.Invoice.subscription",
                }
            ),
        )

    @patch("stripe.Plan.retrieve", autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        autospec=True,
    )
    def test_update_multi_plan(
        self,
        subscription_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION_MULTI_PLAN)
        subscription_fake["latest_invoice"] = FAKE_INVOICE["id"]
        subscription_retrieve_mock.return_value = subscription_fake

        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        self.assertIsNone(subscription.plan)
        self.assertIsNone(subscription.quantity)

        items = subscription.items.all()
        self.assertEqual(2, len(items))

        # Simulate a webhook received with one plan that has been removed
        del subscription_fake["items"]["data"][1]
        subscription_fake["items"]["total_count"] = 1

        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        items = subscription.items.all()
        self.assertEqual(1, len(items))

        # delete pydanny customer as that causes issues with Invoice and Latest_invoice FKs
        self.customer.delete()

        self.assert_fks(
            subscription,
            expected_blank_fks=(
                self.default_expected_blank_fks
                | {
                    "djstripe.Customer.subscriber",
                    "djstripe.Subscription.plan",
                    "djstripe.Charge.latest_upcominginvoice (related name)",
                    "djstripe.Charge.application_fee",
                    "djstripe.Charge.dispute",
                    "djstripe.Charge.on_behalf_of",
                    "djstripe.Charge.source_transfer",
                    "djstripe.Charge.transfer",
                    "djstripe.PaymentIntent.upcominginvoice (related name)",
                    "djstripe.PaymentIntent.on_behalf_of",
                    "djstripe.PaymentIntent.payment_method",
                    "djstripe.Invoice.default_payment_method",
                    "djstripe.Invoice.default_source",
                    "djstripe.Invoice.charge",
                    "djstripe.Invoice.customer",
                    "djstripe.Invoice.payment_intent",
                    "djstripe.Invoice.subscription",
                }
            ),
        )

    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Charge.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_II),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", return_value=deepcopy(FAKE_INVOICE_II), autospec=True
    )
    @patch("stripe.Plan.retrieve", autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        autospec=True,
    )
    def test_remove_all_multi_plan(
        self,
        subscription_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        invoice_retrieve_mock,
        paymentintent_retrieve_mock,
        paymentmethod_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        # delete pydanny customer as that causes issues with Invoice and Latest_invoice FKs
        self.customer.delete()

        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_II)
        fake_payment_intent["invoice"] = FAKE_INVOICE_II["id"]
        paymentintent_retrieve_mock.return_value = fake_payment_intent

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION_MULTI_PLAN)
        fake_subscription["latest_invoice"] = FAKE_INVOICE_II["id"]
        subscription_retrieve_mock.return_value = fake_subscription

        fake_charge = deepcopy(FAKE_CHARGE_II)
        fake_charge["payment_method"] = FAKE_PAYMENT_METHOD_II["id"]
        charge_retrieve_mock.return_value = fake_charge

        # create invoice
        fake_invoice = deepcopy(FAKE_INVOICE_II)
        Invoice.sync_from_stripe_data(fake_invoice)

        subscription = Subscription.sync_from_stripe_data(fake_subscription)

        self.assertIsNone(subscription.plan)
        self.assertIsNone(subscription.quantity)

        items = subscription.items.all()
        self.assertEqual(2, len(items))

        # Simulate a webhook received with no more plan
        del fake_subscription["items"]["data"][1]
        del fake_subscription["items"]["data"][0]
        fake_subscription["items"]["total_count"] = 0

        subscription = Subscription.sync_from_stripe_data(fake_subscription)
        items = subscription.items.all()
        self.assertEqual(0, len(items))

        self.assert_fks(
            subscription,
            expected_blank_fks=self.default_expected_blank_fks
            | {
                "djstripe.Customer.subscriber",
                "djstripe.Subscription.plan",
            },
        )

    @patch("stripe.Plan.retrieve", autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION_METERED)
    )
    def test_sync_metered_plan(
        self,
        subscription_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION_METERED)
        self.assertNotIn(
            "quantity",
            subscription_fake["items"]["data"],
            "Expect Metered plan SubscriptionItem to have no quantity",
        )

        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        assert subscription

        items = subscription.items.all()
        self.assertEqual(1, len(items))

        item = items[0]

        self.assertEqual(subscription.quantity, 1)
        # Note that subscription.quantity is 1,
        # but item.quantity isn't set on metered plans
        self.assertIsNone(item.quantity)
        self.assertEqual(item.plan.id, FAKE_PLAN_METERED["id"])

        self.assert_fks(
            subscription,
            expected_blank_fks=(
                self.default_expected_blank_fks
                | {"djstripe.Subscription.latest_invoice"}
            ),
        )

    @patch("stripe.Subscription.list")
    def test_api_list(self, subscription_list_mock):
        p = PropertyMock(return_value=deepcopy(FAKE_SUBSCRIPTION))
        type(subscription_list_mock).auto_paging_iter = p

        # invoke Subscription.api_list with status enum populated
        Subscription.api_list(status=SubscriptionStatus.canceled)

        subscription_list_mock.assert_called_once_with(
            status=SubscriptionStatus.canceled,
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
        )

    @patch("stripe.Subscription.list")
    def test_api_list_with_no_status(self, subscription_list_mock):
        p = PropertyMock(return_value=deepcopy(FAKE_SUBSCRIPTION))
        type(subscription_list_mock).auto_paging_iter = p

        # invoke Subscription.api_list without status enum populated
        Subscription.api_list()

        subscription_list_mock.assert_called_once_with(
            status="all",
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
        )


class TestSubscriptionDecimal:
    @pytest.mark.parametrize(
        "inputted,expected",
        [
            (Decimal("1"), Decimal("1.00")),
            (Decimal("1.5234567"), Decimal("1.52")),
            (Decimal("0"), Decimal("0.00")),
            (Decimal("23.2345678"), Decimal("23.23")),
            ("1", Decimal("1.00")),
            ("1.5234567", Decimal("1.52")),
            ("0", Decimal("0.00")),
            ("23.2345678", Decimal("23.23")),
            (1, Decimal("1.00")),
            (1.5234567, Decimal("1.52")),
            (0, Decimal("0.00")),
            (23.2345678, Decimal("23.24")),
        ],
    )
    def test_decimal_application_fee_percent(self, inputted, expected, monkeypatch):
        fake_subscription = deepcopy(FAKE_SUBSCRIPTION)
        fake_subscription["application_fee_percent"] = inputted

        def mock_invoice_get(*args, **kwargs):
            return FAKE_INVOICE

        def mock_customer_get(*args, **kwargs):
            return FAKE_CUSTOMER

        def mock_charge_get(*args, **kwargs):
            return FAKE_CHARGE

        def mock_payment_method_get(*args, **kwargs):
            return FAKE_CARD_AS_PAYMENT_METHOD

        def mock_payment_intent_get(*args, **kwargs):
            return FAKE_PAYMENT_INTENT_I

        def mock_subscription_get(*args, **kwargs):
            return fake_subscription

        def mock_balance_transaction_get(*args, **kwargs):
            return FAKE_BALANCE_TRANSACTION

        def mock_product_get(*args, **kwargs):
            return FAKE_PRODUCT

        def mock_plan_get(*args, **kwargs):
            return FAKE_PLAN

        # monkeypatch stripe retrieve calls to return
        # the desired json response.
        monkeypatch.setattr(stripe.Invoice, "retrieve", mock_invoice_get)
        monkeypatch.setattr(stripe.Customer, "retrieve", mock_customer_get)
        monkeypatch.setattr(
            stripe.BalanceTransaction, "retrieve", mock_balance_transaction_get
        )
        monkeypatch.setattr(stripe.Subscription, "retrieve", mock_subscription_get)
        monkeypatch.setattr(stripe.Charge, "retrieve", mock_charge_get)
        monkeypatch.setattr(stripe.PaymentMethod, "retrieve", mock_payment_method_get)
        monkeypatch.setattr(stripe.PaymentIntent, "retrieve", mock_payment_intent_get)
        monkeypatch.setattr(stripe.Product, "retrieve", mock_product_get)
        monkeypatch.setattr(stripe.Plan, "retrieve", mock_plan_get)

        # Create Latest Invoice
        Invoice.sync_from_stripe_data(FAKE_INVOICE)

        subscription = Subscription.sync_from_stripe_data(fake_subscription)
        field_data = subscription.application_fee_percent

        assert isinstance(field_data, Decimal)
        assert field_data == expected
