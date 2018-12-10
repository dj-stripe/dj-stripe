"""
dj-stripe Subscription Model Tests.
"""
from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from stripe.error import InvalidRequestError

from djstripe.enums import SubscriptionStatus
from djstripe.models import Plan, Subscription

from . import (
	FAKE_CUSTOMER, FAKE_CUSTOMER_II, FAKE_PLAN, FAKE_PLAN_II,
	FAKE_SUBSCRIPTION, FAKE_SUBSCRIPTION_CANCELED,
	FAKE_SUBSCRIPTION_MULTI_PLAN, AssertStripeFksMixin, datetime_to_unix
)


class SubscriptionTest(AssertStripeFksMixin, TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="pydanny", email="pydanny@gmail.com"
		)
		self.customer = FAKE_CUSTOMER.create_for_user(self.user)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_str(self, customer_retrieve_mock, plan_retreive_mock):
		subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
		subscription = Subscription.sync_from_stripe_data(subscription_fake)

		self.assertEqual(
			str(subscription),
			"{email} on {plan}".format(email=self.user.email, plan=str(subscription.plan)),
		)

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_is_status_temporarily_current(
		self, customer_retrieve_mock, plan_retreive_mock
	):
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
		self.assertTrue(self.customer.has_active_subscription())
		self.assertTrue(self.customer.has_any_active_subscription())

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_is_status_temporarily_current_false(
		self, customer_retrieve_mock, plan_retreive_mock
	):
		subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
		subscription = Subscription.sync_from_stripe_data(subscription_fake)
		subscription.current_period_end = timezone.now() + timezone.timedelta(days=7)
		subscription.save()

		self.assertTrue(subscription.is_status_current())
		self.assertFalse(subscription.is_status_temporarily_current())
		self.assertTrue(subscription.is_valid())
		self.assertTrue(subscription in self.customer.active_subscriptions)
		self.assertTrue(self.customer.has_active_subscription())
		self.assertTrue(self.customer.has_any_active_subscription())

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_is_status_temporarily_current_false_and_cancelled(
		self, customer_retrieve_mock, plan_retreive_mock
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
		self.assertFalse(self.customer.has_active_subscription())
		self.assertFalse(self.customer.has_any_active_subscription())

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Subscription.retrieve")
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_extend(
		self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock
	):
		subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
		subscription_fake["current_period_end"] = datetime_to_unix(
			timezone.now() - timezone.timedelta(days=20)
		)

		subscription_retrieve_mock.return_value = subscription_fake

		subscription = Subscription.sync_from_stripe_data(subscription_fake)
		self.assertFalse(subscription in self.customer.active_subscriptions)
		self.assertEqual(self.customer.active_subscriptions.count(), 0)

		delta = timezone.timedelta(days=30)
		extended_subscription = subscription.extend(delta)

		self.assertNotEqual(None, extended_subscription.trial_end)
		self.assertTrue(self.customer.has_active_subscription())
		self.assertTrue(self.customer.has_any_active_subscription())

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_extend_negative_delta(
		self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock
	):
		subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
		subscription = Subscription.sync_from_stripe_data(subscription_fake)

		with self.assertRaises(ValueError):
			subscription.extend(timezone.timedelta(days=-30))

		self.assertFalse(self.customer.has_active_subscription())
		self.assertFalse(self.customer.has_any_active_subscription())

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_extend_with_trial(
		self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock
	):
		subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
		subscription = Subscription.sync_from_stripe_data(subscription_fake)
		subscription.trial_end = timezone.now() + timezone.timedelta(days=5)
		subscription.save()

		delta = timezone.timedelta(days=30)
		new_trial_end = subscription.trial_end + delta

		extended_subscription = subscription.extend(delta)

		self.assertEqual(
			new_trial_end.replace(microsecond=0), extended_subscription.trial_end
		)
		self.assertTrue(self.customer.has_active_subscription())
		self.assertTrue(self.customer.has_any_active_subscription())

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_update(
		self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock
	):
		subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
		subscription = Subscription.sync_from_stripe_data(subscription_fake)

		self.assertEqual(1, subscription.quantity)

		new_subscription = subscription.update(quantity=4)

		self.assertEqual(4, new_subscription.quantity)

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Subscription.retrieve")
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_update_set_empty_value(
		self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock
	):
		subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
		subscription_fake.update({"tax_percent": Decimal(20.0)})
		subscription_retrieve_mock.return_value = subscription_fake
		subscription = Subscription.sync_from_stripe_data(subscription_fake)

		self.assertEqual(Decimal(20.0), subscription.tax_percent)

		new_subscription = subscription.update(tax_percent=Decimal(0.0))

		self.assertEqual(Decimal(0.0), new_subscription.tax_percent)

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_update_with_plan_model(
		self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock
	):
		subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
		subscription = Subscription.sync_from_stripe_data(subscription_fake)
		new_plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN_II))

		self.assertEqual(FAKE_PLAN["id"], subscription.plan.id)

		new_subscription = subscription.update(plan=new_plan)

		self.assertEqual(FAKE_PLAN_II["id"], new_subscription.plan.id)

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

		self.assert_fks(new_plan, expected_blank_fks={"djstripe.Plan.product"})

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Subscription.retrieve")
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_cancel_now(
		self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock
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
		subscription_retrieve_mock.return_value = (
			canceled_subscription_fake
		)  # retrieve().delete()

		self.assertTrue(self.customer.has_active_subscription())
		self.assertEqual(self.customer.active_subscriptions.count(), 1)
		self.assertTrue(self.customer.has_any_active_subscription())

		new_subscription = subscription.cancel(at_period_end=False)

		self.assertEqual(SubscriptionStatus.canceled, new_subscription.status)
		self.assertEqual(False, new_subscription.cancel_at_period_end)
		self.assertEqual(new_subscription.canceled_at, new_subscription.ended_at)
		self.assertFalse(new_subscription.is_valid())
		self.assertFalse(new_subscription in self.customer.active_subscriptions)
		self.assertFalse(self.customer.has_active_subscription())
		self.assertFalse(self.customer.has_any_active_subscription())

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Subscription.retrieve")
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_cancel_at_period_end(
		self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock
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
		subscription_retrieve_mock.return_value = (
			canceled_subscription_fake
		)  # retrieve().delete()

		self.assertTrue(self.customer.has_active_subscription())
		self.assertTrue(self.customer.has_any_active_subscription())
		self.assertEqual(self.customer.active_subscriptions.count(), 1)
		self.assertTrue(subscription in self.customer.active_subscriptions)

		new_subscription = subscription.cancel(at_period_end=True)
		self.assertEqual(self.customer.active_subscriptions.count(), 1)
		self.assertTrue(new_subscription in self.customer.active_subscriptions)

		self.assertEqual(SubscriptionStatus.active, new_subscription.status)
		self.assertEqual(True, new_subscription.cancel_at_period_end)
		self.assertNotEqual(new_subscription.canceled_at, new_subscription.ended_at)
		self.assertTrue(new_subscription.is_valid())
		self.assertTrue(self.customer.has_active_subscription())
		self.assertTrue(self.customer.has_any_active_subscription())

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Subscription.retrieve")
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_cancel_during_trial_sets_at_period_end(
		self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock
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
		subscription_retrieve_mock.return_value = (
			canceled_subscription_fake
		)  # retrieve().delete()

		self.assertTrue(self.customer.has_active_subscription())
		self.assertTrue(self.customer.has_any_active_subscription())

		new_subscription = subscription.cancel(at_period_end=False)

		self.assertEqual(SubscriptionStatus.canceled, new_subscription.status)
		self.assertEqual(False, new_subscription.cancel_at_period_end)
		self.assertEqual(new_subscription.canceled_at, new_subscription.ended_at)
		self.assertFalse(new_subscription.is_valid())
		self.assertFalse(self.customer.has_active_subscription())
		self.assertFalse(self.customer.has_any_active_subscription())

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
	@patch("stripe.Subscription.retrieve")
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
	def test_cancel_and_reactivate(
		self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock
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

		self.assertTrue(self.customer.has_active_subscription())
		self.assertTrue(self.customer.has_any_active_subscription())

		new_subscription = subscription.cancel(at_period_end=True)
		self.assertEqual(new_subscription.cancel_at_period_end, True)

		new_subscription.reactivate()
		subscription_reactivate_fake = deepcopy(FAKE_SUBSCRIPTION)
		reactivated_subscription = Subscription.sync_from_stripe_data(
			subscription_reactivate_fake
		)
		self.assertEqual(reactivated_subscription.cancel_at_period_end, False)

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("djstripe.models.Subscription._api_delete")
	@patch(
		"stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION_CANCELED)
	)
	def test_cancel_already_canceled(
		self, subscription_retrieve_mock, subscription_delete_mock
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
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("djstripe.models.Subscription._api_delete")
	def test_cancel_error_in_cancel(self, subscription_delete_mock):
		subscription_delete_mock.side_effect = InvalidRequestError("Unexpected error", "blah")

		subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
		subscription = Subscription.sync_from_stripe_data(subscription_fake)

		with self.assertRaises(InvalidRequestError):
			subscription.cancel(at_period_end=False)

		self.assert_fks(
			subscription,
			expected_blank_fks={"djstripe.Customer.coupon", "djstripe.Plan.product"},
		)

	@patch("stripe.Plan.retrieve")
	@patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER_II))
	@patch(
		"stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION_MULTI_PLAN)
	)
	def test_sync_multi_plan(
		self, subscription_retrieve_mock, customer_retrieve_mock, plan_retrieve_mock
	):
		subscription_fake = deepcopy(FAKE_SUBSCRIPTION_MULTI_PLAN)
		subscription = Subscription.sync_from_stripe_data(subscription_fake)

		self.assertIsNone(subscription.plan)
		self.assertIsNone(subscription.quantity)

		items = subscription.items.all()
		self.assertEqual(2, len(items))
