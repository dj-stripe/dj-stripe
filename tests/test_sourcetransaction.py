"""
dj-stripe SourceTransaction Model Tests.
"""
from copy import deepcopy
from unittest.mock import PropertyMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe import enums
from djstripe.models import Source
from djstripe.models.payment_methods import SourceTransaction
from djstripe.settings import djstripe_settings

from . import (
    FAKE_CUSTOMER_III,
    FAKE_SOURCE,
    FAKE_SOURCE_TRANSACTION,
    AssertStripeFksMixin,
)


class SourceTransactionTest(AssertStripeFksMixin, TestCase):
    def setUp(self):

        user = get_user_model().objects.create_user(
            username="arnav13", email="arnav13@gmail.com"
        )

        # create a source object so that FAKE_CUSTOMER_III with a default source
        # can be created correctly.
        fake_source_data = deepcopy(FAKE_SOURCE)
        fake_source_data["customer"] = None
        self.source = Source.sync_from_stripe_data(fake_source_data)

        self.customer = FAKE_CUSTOMER_III.create_for_user(user)
        self.customer.sources.all().delete()
        self.customer.legacy_cards.all().delete()

    def test_sync_from_stripe_data(self):
        # create the SourceTransaction object
        sourcetransaction = SourceTransaction.sync_from_stripe_data(
            deepcopy(FAKE_SOURCE_TRANSACTION)
        )

        self.assertEqual(sourcetransaction.type, enums.SourceType.ach_credit_transfer)
        self.assertEqual(sourcetransaction.source, self.source)

        self.assert_fks(
            sourcetransaction,
            expected_blank_fks={
                "djstripe.Source.customer",
                "djstripe.Customer.default_payment_method",
            },
        )

    def test___str__(self):
        # create the SourceTransaction object
        sourcetransaction = SourceTransaction.sync_from_stripe_data(
            deepcopy(FAKE_SOURCE_TRANSACTION)
        )
        self.assertEqual(
            f"Source Transaction status={sourcetransaction.status}, source={sourcetransaction.source.id}",
            str(sourcetransaction),
        )

    def test_get_stripe_dashboard_url(self):
        # create the SourceTransaction object
        sourcetransaction_1 = SourceTransaction.sync_from_stripe_data(
            deepcopy(FAKE_SOURCE_TRANSACTION)
        )
        self.assertEqual(
            f"{sourcetransaction_1._get_base_stripe_dashboard_url()}sources/{sourcetransaction_1.source.id}",
            sourcetransaction_1.get_stripe_dashboard_url(),
        ),

        # create the SourceTransaction object
        fake_source_transaction = deepcopy(FAKE_SOURCE_TRANSACTION)
        fake_source_transaction["source"] = None
        sourcetransaction_2 = SourceTransaction.sync_from_stripe_data(
            fake_source_transaction
        )
        self.assertEqual("", sourcetransaction_2.get_stripe_dashboard_url()),

    @patch(
        "stripe.Source.list_source_transactions",
    )
    def test_api_list(self, source_transaction_list_mock):
        p = PropertyMock(return_value=deepcopy(FAKE_SOURCE_TRANSACTION))
        type(source_transaction_list_mock).auto_paging_iter = p

        # invoke the api_list classmethod
        SourceTransaction.api_list(id=self.source.id)
        source_transaction_list_mock.assert_called_once_with(
            id=FAKE_SOURCE["id"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
        )
