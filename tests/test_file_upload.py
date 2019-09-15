from unittest.mock import ANY, call, patch

import pytest

from djstripe.models import Account, FileUpload

from . import FAKE_ACCOUNT, FAKE_FILEUPLOAD_ICON, FAKE_FILEUPLOAD_LOGO


@pytest.mark.django_db
@patch(target="stripe.FileUpload.retrieve", autospec=True)
def test_file_upload_api_retrieve(mock_file_upload_retrieve):
    """Expect file_upload to use the ID of the account referring
    to it to retrieve itself.
    """
    # Create files
    icon_file = FileUpload._get_or_create_from_stripe_object(data=FAKE_FILEUPLOAD_ICON)[
        0
    ]
    logo_file = FileUpload._get_or_create_from_stripe_object(data=FAKE_FILEUPLOAD_LOGO)[
        0
    ]
    # Create account to associate the files to it
    account = Account._get_or_create_from_stripe_object(data=FAKE_ACCOUNT)[0]

    # Call the API retrieve methods.
    icon_file.api_retrieve()
    logo_file.api_retrieve()

    # Ensure the correct Account ID was used in retrieval
    mock_file_upload_retrieve.assert_has_calls(
        (
            call(id=icon_file.id, api_key=ANY, expand=ANY, stripe_account=account.id),
            call(id=logo_file.id, api_key=ANY, expand=ANY, stripe_account=account.id),
        )
    )
