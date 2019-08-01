from django.core.management import call_command
from django.test import TestCase


class TestRunManagePyCheck(TestCase):
    def test_manage_py_check(self):
        call_command("check")
