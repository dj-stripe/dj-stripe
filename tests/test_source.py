"""
dj-stripe Card Model Tests.
"""
import sys
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from djstripe.models import Source

from . import (
    FAKE_CUSTOMER_III,
    FAKE_SOURCE,
    FAKE_SOURCE_II,
    AssertStripeFksMixin,
    SourceDict,
    default_account,
)


class SourceTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        self.account = default_account()
        self.user = get_user_model().objects.create_user(
            username="testuser", email="djstripe@example.com"
        )
        self.customer = FAKE_CUSTOMER_III.create_for_user(self.user)
        self.customer.sources.all().delete()
        self.customer.legacy_cards.all().delete()

    def test_attach_objects_hook_without_customer(self):
        source = Source.sync_from_stripe_data(deepcopy(FAKE_SOURCE_II))
        self.assertEqual(source.customer, None)

        self.assert_fks(
            source,
            expected_blank_fks={
                "djstripe.Source.customer",
                "djstripe.Customer.default_payment_method",
            },
        )

    def test_sync_source_finds_customer(self):
        source = Source.sync_from_stripe_data(deepcopy(FAKE_SOURCE))

        self.assertEqual(self.customer, source.customer)

        self.assert_fks(
            source,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
            },
        )

    def test_str(self):
        fake_source = deepcopy(FAKE_SOURCE)
        source = Source.sync_from_stripe_data(fake_source)

        self.assertEqual("<id={}>".format(fake_source["id"]), str(source))

        self.assert_fks(
            source,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
            },
        )

    @patch("stripe.Source.retrieve", return_value=deepcopy(FAKE_SOURCE), autospec=True)
    def test_detach(self, source_retrieve_mock):
        original_detach = SourceDict.detach

        def mocked_detach(self):
            return original_detach(self)

        Source.sync_from_stripe_data(deepcopy(FAKE_SOURCE))

        self.assertEqual(0, self.customer.legacy_cards.count())
        self.assertEqual(1, self.customer.sources.count())

        source = self.customer.sources.first()

        with patch(
            "tests.SourceDict.detach", side_effect=mocked_detach, autospec=True
        ) as mock_detach:
            source.detach()

        self.assertEqual(0, self.customer.sources.count())
        # need to refresh_from_db since default_source was cleared with a query
        self.customer.refresh_from_db()
        self.assertIsNone(self.customer.default_source)

        # need to refresh_from_db due to the implementation of Source.detach() -
        # see TODO in method
        source.refresh_from_db()
        self.assertIsNone(source.customer)
        self.assertEqual(source.status, "consumed")

        if sys.version_info >= (3, 6):
            # this mock isn't working on py34, py35, but it's not strictly necessary
            # for the test
            mock_detach.assert_called()

        self.assert_fks(
            source,
            expected_blank_fks={
                "djstripe.Source.customer",
                "djstripe.Customer.default_payment_method",
            },
        )
