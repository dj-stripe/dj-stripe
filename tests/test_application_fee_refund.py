"""
dj-stripe ApplicationFeeRefund model tests.

Refunds are nested under their application fee in the Stripe API, and
stripe.ApplicationFeeRefund has no `list` or `create` (its `retrieve` raises
NotImplementedError), so every call has to go through stripe.ApplicationFee.
"""

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test import TestCase

from djstripe.management.commands.djstripe_sync_models import Command
from djstripe.models import ApplicationFee, ApplicationFeeRefund
from djstripe.settings import djstripe_settings

from . import StripeItem, StripeList

pytestmark = pytest.mark.django_db

FEE_ID = "fee_1"
REFUND_ID = "fr_1"


class ApplicationFeeRefundApiTest(TestCase):
    @patch("stripe.ApplicationFee.list_refunds", autospec=True)
    def test_api_list_lists_the_refunds_of_one_fee(self, list_refunds_mock):
        list_refunds_mock.return_value = StripeList(data=[])

        ApplicationFeeRefund.api_list(id=FEE_ID, api_key="sk_test_x")

        args, kwargs = list_refunds_mock.call_args
        # The fee id is a path parameter, which stripe-python 16+ only accepts
        # positionally.
        assert args == (FEE_ID,)
        assert "id" not in kwargs
        assert kwargs["api_key"] == "sk_test_x"
        assert kwargs["stripe_version"] == djstripe_settings.STRIPE_API_VERSION

    @patch("stripe.ApplicationFee.retrieve_refund", autospec=True)
    def test_api_retrieve_goes_through_the_fee(self, retrieve_refund_mock):
        refund = ApplicationFeeRefund(id=REFUND_ID, fee=ApplicationFee(id=FEE_ID))

        refund.api_retrieve(api_key="sk_test_x", stripe_account="acct_1")

        retrieve_refund_mock.assert_called_once_with(
            FEE_ID,
            REFUND_ID,
            api_key="sk_test_x",
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
            expand=refund.expand_fields,
            stripe_account="acct_1",
        )

    @patch("stripe.ApplicationFee.create_refund", autospec=True)
    def test_api_create_refunds_the_fee(self, create_refund_mock):
        ApplicationFeeRefund._api_create(id=FEE_ID, api_key="sk_test_x", amount=100)

        create_refund_mock.assert_called_once_with(
            FEE_ID,
            api_key="sk_test_x",
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
            amount=100,
        )


class ApplicationFeeRefundSyncTest(TestCase):
    SK_TEST = "sk_test_" + "a" * 24

    def test_sync_models_lists_refunds_for_each_fee(self):
        fees = StripeList(data=[StripeItem(id="fee_1"), StripeItem(id="fee_2")])
        refunds = {
            "fee_1": [StripeItem(id="fr_1", object="fee_refund")],
            "fee_2": [StripeItem(id="fr_2", object="fee_refund")],
        }
        stderr = StringIO()

        with (
            patch.object(Command, "get_stripe_account", return_value={""}),
            patch.object(ApplicationFee, "api_list", return_value=fees),
            patch(
                "stripe.ApplicationFee.list_refunds",
                autospec=True,
                side_effect=lambda fee_id, **kwargs: StripeList(data=refunds[fee_id]),
            ) as list_refunds_mock,
            patch.object(
                ApplicationFeeRefund,
                "sync_from_stripe_data",
                side_effect=lambda data, **kwargs: ApplicationFeeRefund(id=data.id),
            ) as sync_mock,
        ):
            call_command(
                "djstripe_sync_models",
                "ApplicationFeeRefund",
                api_keys=[self.SK_TEST],
                stdout=StringIO(),
                stderr=stderr,
            )

        assert stderr.getvalue() == ""
        assert [call.args[0] for call in list_refunds_mock.call_args_list] == [
            "fee_1",
            "fee_2",
        ]
        assert [call.args[0].id for call in sync_mock.call_args_list] == [
            "fr_1",
            "fr_2",
        ]
