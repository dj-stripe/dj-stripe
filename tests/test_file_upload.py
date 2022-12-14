"""
dj-stripe File model tests
"""
from copy import deepcopy
from unittest.mock import ANY, call, patch

import pytest
from django.test import TestCase

from djstripe.enums import FilePurpose
from djstripe.models import Account, File
from djstripe.settings import djstripe_settings

from . import FAKE_ACCOUNT, FAKE_FILEUPLOAD_ICON, FAKE_FILEUPLOAD_LOGO

pytestmark = pytest.mark.django_db


class TestFileLink(TestCase):
    @patch(
        target="stripe.File.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
    )
    def test_file_upload_api_retrieve(self, mock_file_upload_retrieve):
        """Expect file_upload to use the ID of the account referring
        to it to retrieve itself.
        """
        # Create files
        icon_file = File._get_or_create_from_stripe_object(data=FAKE_FILEUPLOAD_ICON)[0]
        logo_file = File._get_or_create_from_stripe_object(data=FAKE_FILEUPLOAD_LOGO)[0]
        # Create account to associate the files to it
        account = Account._get_or_create_from_stripe_object(data=FAKE_ACCOUNT)[0]

        # Call the API retrieve methods.
        icon_file.api_retrieve()
        logo_file.api_retrieve()

        # Ensure the correct Account ID was used in retrieval
        mock_file_upload_retrieve.assert_has_calls(
            (
                call(
                    id=icon_file.id,
                    api_key=ANY,
                    expand=ANY,
                    stripe_account=account.id,
                    stripe_version=djstripe_settings.STRIPE_API_VERSION,
                ),
                call(
                    id=logo_file.id,
                    api_key=ANY,
                    expand=ANY,
                    stripe_account=account.id,
                    stripe_version=djstripe_settings.STRIPE_API_VERSION,
                ),
            )
        )

    @patch(
        target="stripe.File.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
    )
    def test_sync_from_stripe_data(self, mock_file_upload_retrieve):
        file = File.sync_from_stripe_data(deepcopy(FAKE_FILEUPLOAD_ICON))

        mock_file_upload_retrieve.assert_not_called()

        assert file.id == FAKE_FILEUPLOAD_ICON["id"]
        assert file.purpose == FAKE_FILEUPLOAD_ICON["purpose"]
        assert file.type == FAKE_FILEUPLOAD_ICON["type"]


class TestFileUploadStr:
    @pytest.mark.parametrize("file_purpose", FilePurpose.__members__)
    def test___str__(self, file_purpose):
        modified_file_data = deepcopy(FAKE_FILEUPLOAD_ICON)
        modified_file_data["purpose"] = file_purpose

        file = File.sync_from_stripe_data(modified_file_data)
        assert (
            f"{modified_file_data['filename']}, {FilePurpose.humanize(modified_file_data['purpose'])}"
        ) == str(file)
