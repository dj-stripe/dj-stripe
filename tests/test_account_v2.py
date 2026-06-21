"""
dj-stripe Account v2 (Stripe Accounts v2 / Organizations) tests.
"""

from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest
from django.test.testcases import TestCase

from djstripe.management.commands.djstripe_sync_models import Command
from djstripe.models import AccountV2

from .conftest import CreateAccountMixin

pytestmark = pytest.mark.django_db


FAKE_ACCOUNT_V2 = {
    "id": "acct_v2_fakefakefake0001",
    "object": "v2.core.account",
    "applied_configurations": ["merchant"],
    "closed": False,
    "configuration": {
        "merchant": {"card_payments": {"status": "active"}},
    },
    "contact_email": "org@example.com",
    "contact_phone": None,
    "created": "2024-01-02T03:04:05.000Z",
    "dashboard": "full",
    "defaults": {"currency": "usd"},
    "display_name": "Example Organization",
    "future_requirements": None,
    "identity": {"business_details": {"registered_name": "Example Org Inc."}},
    "livemode": False,
    "metadata": {"internal_id": "42"},
    "requirements": {"collected": []},
}


class TestAccountV2Sync(CreateAccountMixin, TestCase):
    def test_sync_from_stripe_data_creates_account(self):
        account = AccountV2.sync_from_stripe_data(deepcopy(FAKE_ACCOUNT_V2))

        assert account.id == FAKE_ACCOUNT_V2["id"]
        assert account.display_name == "Example Organization"
        assert account.contact_email == "org@example.com"
        assert account.dashboard == "full"
        assert account.applied_configurations == ["merchant"]
        assert account.closed is False
        assert account.configuration["merchant"]["card_payments"]["status"] == "active"
        assert account.identity["business_details"]["registered_name"] == (
            "Example Org Inc."
        )
        assert account.defaults == {"currency": "usd"}
        assert account.metadata == {"internal_id": "42"}
        assert account.livemode is False
        assert str(account) == "Example Organization"

    def test_created_parsed_from_iso8601_string(self):
        # v2 returns ``created`` as an RFC 3339 string, not a unix timestamp.
        account = AccountV2.sync_from_stripe_data(deepcopy(FAKE_ACCOUNT_V2))

        assert account.created is not None
        assert account.created.year == 2024
        assert account.created.month == 1
        assert account.created.day == 2
        # The original string is preserved verbatim in stripe_data.
        assert account.stripe_data["created"] == "2024-01-02T03:04:05.000Z"


class TestAccountV2API(TestCase):
    def _instance(self):
        return AccountV2(
            id=FAKE_ACCOUNT_V2["id"], stripe_data=deepcopy(FAKE_ACCOUNT_V2)
        )

    def test_api_retrieve_uses_v2_service_with_include(self):
        service = MagicMock()
        with patch.object(AccountV2, "_v2_accounts", return_value=service) as svc:
            self._instance().api_retrieve(api_key="sk_test_xxx")

        svc.assert_called_once_with("sk_test_xxx")
        service.retrieve.assert_called_once_with(
            FAKE_ACCOUNT_V2["id"],
            params={"include": list(AccountV2.DEFAULT_INCLUDE)},
        )

    def test_api_list_ignores_v1_kwargs_and_includes_subresources(self):
        service = MagicMock()
        service.list.return_value.auto_paging_iter.return_value = iter([])
        with patch.object(AccountV2, "_v2_accounts", return_value=service):
            list(
                AccountV2.api_list(
                    api_key="sk_test_xxx",
                    # v1-style kwargs the sync command passes must be ignored
                    expand=["data.foo"],
                    stripe_account="acct_platform",
                )
            )

        service.list.assert_called_once_with(
            params={"include": list(AccountV2.DEFAULT_INCLUDE)}
        )

    def test_api_close_calls_service_close(self):
        service = MagicMock()
        with patch.object(AccountV2, "_v2_accounts", return_value=service):
            self._instance().api_close(api_key="sk_test_xxx")

        service.close.assert_called_once_with(FAKE_ACCOUNT_V2["id"], params=None)

    def test_api_delete_closes(self):
        service = MagicMock()
        with patch.object(AccountV2, "_v2_accounts", return_value=service):
            self._instance()._api_delete(api_key="sk_test_xxx")

        service.close.assert_called_once()


class TestAccountV2SyncCommand(TestCase):
    def test_should_sync_model_returns_true(self):
        # AccountV2's stripe_class has no ``list`` classmethod (the v2 service
        # does), so it must be explicitly allowed by the sync command.
        should_sync, reason = Command()._should_sync_model(AccountV2)
        assert should_sync, reason
