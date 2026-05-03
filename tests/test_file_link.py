"""
dj-stripe FileLink model tests
"""

from copy import deepcopy
from unittest.mock import patch

import pytest
from django.test import TestCase

from djstripe.models import File, FileLink
from djstripe.settings import djstripe_settings

from . import FAKE_FILEUPLOAD_ICON
from .conftest import CreateAccountMixin

pytestmark = pytest.mark.django_db


class TestFileLink(CreateAccountMixin, TestCase):
    @patch(
        target="stripe.File.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
    )
    @patch(
        target="stripe.FileLink.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON["links"]["data"][0]),
    )
    def test___str__(self, mock_file_link_retrieve, mock_file_upload_retrieve):
        file_link_data = deepcopy(FAKE_FILEUPLOAD_ICON["links"]["data"][0])
        file_link = FileLink.sync_from_stripe_data(file_link_data)
        # FileLink.__str__ now returns just the URL.
        assert str(file_link) == file_link_data["url"]

    @patch(
        target="stripe.File.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON),
    )
    @patch(
        target="stripe.FileLink.retrieve",
        autospec=True,
        return_value=deepcopy(FAKE_FILEUPLOAD_ICON["links"]["data"][0]),
    )
    def test_sync_from_stripe_data(
        self, mock_file_link_retrieve, mock_file_upload_retrieve
    ):
        file_link_data = deepcopy(FAKE_FILEUPLOAD_ICON["links"]["data"][0])
        file_link = FileLink.sync_from_stripe_data(file_link_data)

        mock_file_link_retrieve.assert_not_called()
        mock_file_upload_retrieve.assert_called_once()
        assert (
            mock_file_upload_retrieve.call_args.kwargs["id"] == file_link_data["file"]
        )
        assert file_link.file == File.objects.get(id=file_link_data["file"])
        assert file_link.url == file_link_data["url"]
