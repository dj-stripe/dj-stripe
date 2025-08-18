from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings


class TestRunManagePyCheck(TestCase):
    @override_settings(
        STRIPE_TEST_SECRET_KEY="sk_test_foo",
        STRIPE_LIVE_SECRET_KEY="sk_live_foo",
        STRIPE_TEST_PUBLIC_KEY="pk_test_foo",
        STRIPE_LIVE_PUBLIC_KEY="pk_live_foo",
        STRIPE_LIVE_MODE=True,
    )
    def test_manage_py_check(self):
        call_command("check")
