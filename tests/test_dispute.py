"""
dj-stripe Dispute model tests
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.test.testcases import TestCase

from djstripe import enums
from djstripe.models.core import Dispute
from djstripe.settings import djstripe_settings

from . import FAKE_DISPUTE, FAKE_FILEUPLOAD_ICON

pytestmark = pytest.mark.django_db


class TestDisputeStr:
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Dispute.retrieve", return_value=deepcopy(FAKE_DISPUTE), autospec=True
    )
    def test___str__(
        self,
        dispute_retrieve_mock,
        file_retrieve_mock,
    ):

        dispute = Dispute.sync_from_stripe_data(FAKE_DISPUTE)
        assert (
            str(dispute)
            == f"{dispute.human_readable_amount} ({enums.DisputeStatus.humanize(FAKE_DISPUTE['status'])}) "
        )


class TestDispute(TestCase):
    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Dispute.retrieve", return_value=deepcopy(FAKE_DISPUTE), autospec=True
    )
    def test_sync_from_stripe_data(
        self,
        dispute_retrieve_mock,
        file_retrieve_mock,
    ):

        dispute = Dispute.sync_from_stripe_data(FAKE_DISPUTE)
        assert dispute.id == FAKE_DISPUTE["id"]

    @patch(
        "stripe.File.retrieve",
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
        autospec=True,
    )
    @patch(
        "stripe.Dispute.retrieve", return_value=deepcopy(FAKE_DISPUTE), autospec=True
    )
    def test__attach_objects_post_save_hook(
        self,
        dispute_retrieve_mock,
        file_retrieve_mock,
    ):

        dispute = Dispute.sync_from_stripe_data(FAKE_DISPUTE)
        assert dispute.id == FAKE_DISPUTE["id"]

        # assert File was retrieved correctly
        file_retrieve_mock.assert_called_once_with(
            id=FAKE_DISPUTE["evidence"]["receipt"],
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            expand=[],
            stripe_account=None,
        )
