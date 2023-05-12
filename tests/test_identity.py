"""
dj-stripe tests for the identity.py module
"""
from copy import deepcopy
from unittest.mock import patch

import pytest
from django.test.testcases import TestCase

from djstripe.models.identity import VerificationReport, VerificationSession
from djstripe.settings import djstripe_settings

from . import (
    FAKE_ACCOUNT,
    FAKE_VERIFICATION_REPORT,
    FAKE_VERIFICATION_SESSION,
    AssertStripeFksMixin,
)

pytestmark = pytest.mark.django_db
from .conftest import CreateAccountMixin


class TestVerificationReport(CreateAccountMixin, AssertStripeFksMixin, TestCase):
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.identity.VerificationSession.retrieve",
        return_value=deepcopy(FAKE_VERIFICATION_SESSION),
        autospec=True,
    )
    def test_sync_from_stripe_data(
        self,
        verification_session_retrieve_mock,
        account_retrieve_mock,
    ):
        fake_verification_report_data = deepcopy(FAKE_VERIFICATION_REPORT)

        fake_verification_report = VerificationReport.sync_from_stripe_data(
            fake_verification_report_data
        )

        self.assertEqual(
            fake_verification_report.id, fake_verification_report_data["id"]
        )

        self.assertEqual(
            fake_verification_report.verification_session.id,
            fake_verification_report_data["verification_session"],
        )

        self.assert_fks(
            fake_verification_report,
            expected_blank_fks={},
        )


class TestVerificationSession(CreateAccountMixin, AssertStripeFksMixin, TestCase):
    @patch(
        "stripe.Account.retrieve",
        return_value=deepcopy(FAKE_ACCOUNT),
        autospec=True,
    )
    @patch(
        "stripe.identity.VerificationReport.retrieve",
        return_value=deepcopy(FAKE_VERIFICATION_REPORT),
        autospec=True,
    )
    def test_sync_from_stripe_data(
        self,
        verification_report_retrieve_mock,
        account_retrieve_mock,
    ):
        fake_verification_session_data = deepcopy(FAKE_VERIFICATION_SESSION)

        fake_verification_session = VerificationSession.sync_from_stripe_data(
            fake_verification_session_data
        )

        self.assertEqual(
            fake_verification_session.id, fake_verification_session_data["id"]
        )

        self.assertEqual(
            fake_verification_session.last_verification_report.id,
            fake_verification_session_data["last_verification_report"]["id"],
        )

        self.assert_fks(
            fake_verification_session,
            expected_blank_fks={},
        )
