"""
dj-stripe Subscription Model Tests.
"""
from copy import deepcopy
from datetime import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from stripe.error import InvalidRequestError

from djstripe.enums import SubscriptionStatus
from djstripe.models import Plan, Product, Subscription

from . import (
    FAKE_CARD,
    FAKE_CUSTOMER,
    FAKE_CUSTOMER_II,
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

        subscription_fake_1 = deepcopy(FAKE_SUBSCRIPTION_III)
        subscription_fake_1["current_period_end"] += int(
            datetime.timestamp(timezone.now())
        )
        subscription_fake_2 = deepcopy(FAKE_SUBSCRIPTION_II)
        subscription_fake_2["current_period_end"] += int(
            datetime.timestamp(timezone.now())
        )
        subscription_fake_2["customer"] = self.customer.id

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
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

        self.default_expected_blank_fks = {
            "djstripe.Customer.coupon",
            "djstripe.Customer.default_payment_method",
            "djstripe.Subscription.default_payment_method",
            "djstripe.Subscription.default_source",
            "djstripe.Subscription.pending_setup_intent",
            "djstripe.Subscription.schedule",
        }

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_from_stripe_data(
        self, customer_retrieve_mock, product_retrieve_mock, plan_retrieve_mock
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["cancel_at"] = 1624553655
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        self.assertEqual(subscription.default_tax_rates.count(), 1)
        self.assertEqual(
            subscription.default_tax_rates.first().id, FAKE_TAX_RATE_EXAMPLE_1_VAT["id"]
        )

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )
        self.assertEqual(datetime_to_unix(subscription.cancel_at), 1624553655)

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
    def test_sync_items_with_tax_rates(
        self, customer_retrieve_mock, product_retrieve_mock, plan_retrieve_mock
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION_II)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

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
        return_value=deepcopy(FAKE_SUBSCRIPTION_MULTI_PLAN),
    )
    def test_sync_multi_plan(
        self,
        subscription_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION_MULTI_PLAN)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        self.assertIsNone(subscription.plan)
        self.assertIsNone(subscription.quantity)

        items = subscription.items.all()
        self.assertEqual(2, len(items))

        self.assert_fks(
            subscription,
            expected_blank_fks=self.default_expected_blank_fks
            | {"djstripe.Customer.subscriber", "djstripe.Subscription.plan"},
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
        return_value=deepcopy(FAKE_SUBSCRIPTION_MULTI_PLAN),
    )
    def test_update_multi_plan(
        self,
        subscription_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION_MULTI_PLAN)
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

        self.assert_fks(
            subscription,
            expected_blank_fks=self.default_expected_blank_fks
            | {"djstripe.Customer.subscriber", "djstripe.Subscription.plan"},
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
        return_value=deepcopy(FAKE_SUBSCRIPTION_MULTI_PLAN),
    )
    def test_remove_all_multi_plan(
        self,
        subscription_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION_MULTI_PLAN)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        self.assertIsNone(subscription.plan)
        self.assertIsNone(subscription.quantity)

        items = subscription.items.all()
        self.assertEqual(2, len(items))

        # Simulate a webhook received with no more plan
        del subscription_fake["items"]["data"][1]
        del subscription_fake["items"]["data"][0]
        subscription_fake["items"]["total_count"] = 0

        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        items = subscription.items.all()
        self.assertEqual(0, len(items))

        self.assert_fks(
            subscription,
            expected_blank_fks=self.default_expected_blank_fks
            | {"djstripe.Customer.subscriber", "djstripe.Subscription.plan"},
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

        items = subscription.items.all()
        self.assertEqual(1, len(items))

        item = items[0]

        self.assertEqual(subscription.quantity, 1)
        # Note that subscription.quantity is 1,
        # but item.quantity isn't set on metered plans
        self.assertIsNone(item.quantity)
        self.assertEqual(item.plan.id, FAKE_PLAN_METERED["id"])

        self.assert_fks(
            subscription, expected_blank_fks=self.default_expected_blank_fks
        )
