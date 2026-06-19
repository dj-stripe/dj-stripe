"""
Tests for the ``stripe_listen`` management command.
"""

from unittest.mock import MagicMock, patch
from urllib.parse import urlsplit
from uuid import UUID

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

FIXED_UUID = UUID("12345678-1234-5678-1234-567812345678")
COMMAND = "djstripe.management.commands.stripe_listen"


def run_stripe_listen():
    """
    Run the command with the Stripe CLI subprocess mocked out, returning the
    URL that gets passed to ``stripe listen --forward-to``.
    """
    captured = {}

    def fake_run(cmd, *args, **kwargs):
        captured["forward_to"] = cmd[cmd.index("--forward-to") + 1]
        return MagicMock()

    # Mock `stripe listen --print-secret`: first stdout line is the secret.
    popen_mock = MagicMock()
    popen_mock.stdout.readline.return_value = "whsec_testsecret\n"
    popen_mock.stdout.__iter__.return_value = iter([])

    with (
        patch(f"{COMMAND}.stripe_binary_exists", return_value=True),
        patch(f"{COMMAND}.subprocess.Popen", return_value=popen_mock),
        patch(f"{COMMAND}.subprocess.run", side_effect=fake_run),
        patch(f"{COMMAND}.uuid4", return_value=FIXED_UUID),
    ):
        call_command("stripe_listen")

    return captured["forward_to"]


class TestStripeListenCommand(TestCase):
    """Regression tests for the double-slash forward URL (#2195)."""

    def test_forward_url_has_no_double_slash(self):
        # End-to-end against the real URLconf (APPEND_SLASH defaults to True,
        # so the route carries a trailing slash).
        url = run_stripe_listen()

        path = urlsplit(url).path
        self.assertNotIn("//", path, url)
        # The forwarded URL must point at the actual webhook route.
        expected_path = reverse(
            "djstripe:djstripe_webhook_by_uuid", kwargs={"uuid": FIXED_UUID}
        )
        self.assertEqual(path, expected_path)
        self.assertEqual(url, f"http://localhost:8000{expected_path}")

    @patch(f"{COMMAND}.reverse", return_value=f"/djstripe/webhook/{FIXED_UUID}")
    def test_forward_url_without_trailing_slash(self, _reverse_mock):
        # Simulates APPEND_SLASH=False, where the route has no trailing slash
        # (djstripe.urls resolves the slash at import time, so it can't be
        # toggled with override_settings here).
        url = run_stripe_listen()

        self.assertNotIn("//", urlsplit(url).path, url)
        self.assertEqual(url, f"http://localhost:8000/djstripe/webhook/{FIXED_UUID}")
