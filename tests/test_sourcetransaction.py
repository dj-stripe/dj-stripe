from copy import deepcopy

from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe import enums
from djstripe.models import Source
from djstripe.models.payment_methods import SourceTransaction

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
