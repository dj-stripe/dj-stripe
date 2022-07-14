"""
dj-stripe UsageRecordSummary model tests
"""
from copy import deepcopy
from unittest.mock import PropertyMock, call, patch

import pytest
from django.test.testcases import TestCase

from djstripe.models.billing import UsageRecordSummary
from djstripe.settings import djstripe_settings

from . import (
    FAKE_CUSTOMER_II,
    FAKE_INVOICE_METERED_SUBSCRIPTION,
    FAKE_INVOICE_METERED_SUBSCRIPTION_USAGE,
    FAKE_INVOICEITEM,
    FAKE_INVOICEITEM_II,
    FAKE_LINE_ITEM,
    FAKE_PLAN_METERED,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION_ITEM,
    FAKE_USAGE_RECORD_SUMMARY,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db


class TestUsageRecordSummary(AssertStripeFksMixin, TestCase):
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
    def test_sync_from_stripe_data_with_null_invoice(
        self,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        fake_usage_data = deepcopy(FAKE_USAGE_RECORD_SUMMARY)

        usage_record_summary = UsageRecordSummary.sync_from_stripe_data(
            fake_usage_data["data"][0]
        )

        self.assertEqual(usage_record_summary.id, fake_usage_data["data"][0]["id"])
        self.assertEqual(
            usage_record_summary.subscription_item.id,
            fake_usage_data["data"][0]["subscription_item"],
        )

        self.assert_fks(
            usage_record_summary,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
                "djstripe.Product.default_price",
                "djstripe.Subscription.default_payment_method",
                "djstripe.Subscription.default_source",
                "djstripe.Subscription.pending_setup_intent",
                "djstripe.Subscription.schedule",
                "djstripe.Subscription.latest_invoice",
                "djstripe.UsageRecordSummary.invoice",
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
    @patch(
        "stripe.LineItem.retrieve",
        return_value=deepcopy(FAKE_LINE_ITEM),
        autospec=True,
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM_II),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve",
        return_value=deepcopy(FAKE_INVOICE_METERED_SUBSCRIPTION),
        autospec=True,
    )
    def test_sync_from_stripe_data(
        self,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        line_item_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        fake_usage_data = deepcopy(FAKE_USAGE_RECORD_SUMMARY)

        usage_record_summary = UsageRecordSummary.sync_from_stripe_data(
            fake_usage_data["data"][1]
        )

        self.assertEqual(usage_record_summary.id, fake_usage_data["data"][1]["id"])
        self.assertEqual(
            usage_record_summary.subscription_item.id,
            fake_usage_data["data"][1]["subscription_item"],
        )

        self.assert_fks(
            usage_record_summary,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
                "djstripe.Product.default_price",
                "djstripe.Subscription.default_payment_method",
                "djstripe.Subscription.default_source",
                "djstripe.Subscription.pending_setup_intent",
                "djstripe.Subscription.schedule",
                "djstripe.Subscription.latest_invoice",
                "djstripe.Invoice.default_payment_method",
                "djstripe.Invoice.default_source",
                "djstripe.Invoice.payment_intent",
                "djstripe.Invoice.charge",
            },
        )

        # assert invoice_retrieve_mock was called like so:
        invoice_retrieve_mock.assert_has_calls(
            [
                call(
                    id=FAKE_INVOICE_METERED_SUBSCRIPTION["id"],
                    api_key=djstripe_settings.STRIPE_SECRET_KEY,
                    expand=[],
                    stripe_account=None,
                ),
                call(
                    id="in_16af5A2eZvKYlo2CJjANLL81",
                    api_key=djstripe_settings.STRIPE_SECRET_KEY,
                    expand=[],
                    stripe_account=None,
                ),
            ]
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
    @patch(
        "stripe.LineItem.retrieve",
        return_value=deepcopy(FAKE_LINE_ITEM),
        autospec=True,
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve",
        return_value=deepcopy(FAKE_INVOICE_METERED_SUBSCRIPTION),
        autospec=True,
    )
    def test___str__(
        self,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        line_item_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        fake_usage_data = deepcopy(FAKE_USAGE_RECORD_SUMMARY)

        usage_record_summary = UsageRecordSummary.sync_from_stripe_data(
            fake_usage_data["data"][1]
        )

        self.assertEqual(
            str(usage_record_summary),
            f"Usage Summary for {str(usage_record_summary.subscription_item)} ({str(usage_record_summary.invoice)}) is {fake_usage_data['data'][1]['total_usage']}",
        )

    @patch(
        "stripe.SubscriptionItem.list_usage_record_summaries",
        autospec=True,
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
    @patch(
        "stripe.Invoice.retrieve",
        return_value=deepcopy(FAKE_INVOICE_METERED_SUBSCRIPTION),
        autospec=True,
    )
    def test_api_list(
        self,
        invoice_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        customer_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        subcription_item_get_mock,
        usage_record_list_mock,
    ):
        p = PropertyMock(return_value=deepcopy(FAKE_USAGE_RECORD_SUMMARY))
        type(usage_record_list_mock).auto_paging_iter = p

        fake_usage_data = deepcopy(FAKE_USAGE_RECORD_SUMMARY)

        UsageRecordSummary.api_list(id=fake_usage_data["data"][1]["subscription_item"])

        # assert usage_record_list_mock was called as expected
        usage_record_list_mock.assert_called_once_with(
            id=fake_usage_data["data"][1]["subscription_item"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
        )
