"""
dj-stripe UsageRecord model tests
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.test.testcases import TestCase

from djstripe.models.billing import UsageRecord
from djstripe.settings import djstripe_settings

from . import (
    FAKE_CUSTOMER_II,
    FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE,
    FAKE_PLAN_METERED,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION_ITEM,
    FAKE_USAGE_RECORD,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


class TestUsageRecord(AssertStripeFksMixin, TestCase):
    @patch(
        "stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN_METERED), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_ITEM),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE),
        autospec=True,
    )
    def test_sync_from_stripe_data(
        self,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        fake_usage_data = deepcopy(FAKE_USAGE_RECORD)

        usage_record = UsageRecord.sync_from_stripe_data(fake_usage_data)
        assert usage_record

        self.assertEqual(usage_record.id, fake_usage_data["id"])
        self.assertEqual(
            usage_record.subscription_item.id, fake_usage_data["subscription_item"]
        )

        self.assert_fks(
            usage_record,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
                "djstripe.Subscription.default_payment_method",
                "djstripe.Subscription.default_source",
                "djstripe.Subscription.pending_setup_intent",
                "djstripe.Subscription.schedule",
                "djstripe.Subscription.latest_invoice",
            },
        )

    @patch(
        "stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN_METERED), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_ITEM),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE),
        autospec=True,
    )
    def test___str__(
        self,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        fake_usage_data = deepcopy(FAKE_USAGE_RECORD)

        usage_record = UsageRecord.sync_from_stripe_data(fake_usage_data)
        assert usage_record

        self.assertEqual(
            str(usage_record),
            f"Usage for {str(usage_record.subscription_item)} ({fake_usage_data['action']}) is {fake_usage_data['quantity']}",
        )

    @patch(
        "stripe.SubscriptionItem.create_usage_record",
        autospec=True,
        return_value=deepcopy(FAKE_USAGE_RECORD),
    )
    @patch(
        "djstripe.models.billing.UsageRecord.sync_from_stripe_data",
        return_value=deepcopy(FAKE_SUBSCRIPTION_ITEM),
    )
    @patch(
        "djstripe.models.billing.SubscriptionItem.objects.get",
        return_value=deepcopy(FAKE_SUBSCRIPTION_ITEM),
    )
    @patch(
        "stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN_METERED), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER_II),
        autospec=True,
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_ITEM),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE),
        autospec=True,
    )
    def test__api_create(
        self,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        subcription_item_get_mock,
        sync_from_stripe_data_mock,
        usage_record_creation_mock,
    ):
        fake_usage_data = deepcopy(FAKE_USAGE_RECORD)

        UsageRecord._api_create(id=fake_usage_data["subscription_item"])

        # assert usage_record_creation_mock was called as expected
        usage_record_creation_mock.assert_called_once_with(
            id=fake_usage_data["subscription_item"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
        )

        # assert usage_record_creation_mock was called as expected
        sync_from_stripe_data_mock.assert_called_once_with(
            fake_usage_data, api_key=djstripe_settings.STRIPE_SECRET_KEY
        )
