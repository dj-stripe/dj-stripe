"""
Tests for JSONField

Due to their nature messing with subclassing, these tests must be run last.
"""
import sys
from importlib import reload
from unittest import skipUnless

from django.test import TestCase
from django.test.utils import override_settings
from jsonfield import JSONField as UglyJSONField

from djstripe import fields as fields
from djstripe import settings as djstripe_settings

try:
    from django.contrib.postgres.fields import JSONField as DjangoJSONField
except ImportError:
    pass


@override_settings(DJSTRIPE_USE_NATIVE_JSONFIELD=False)
class TestFallbackJSONField(TestCase):
    def test_jsonfield_inheritance(self):
        reload(djstripe_settings)
        reload(fields)

        self.assertTrue(issubclass(fields.JSONField, UglyJSONField))

    def tearDown(self):
        reload(djstripe_settings)
        reload(fields)


@skipUnless("psycopg2" in sys.modules, "psycopg2 isn't present")
@override_settings(DJSTRIPE_USE_NATIVE_JSONFIELD=True)
class TestNativeJSONField(TestCase):
    def test_jsonfield_inheritance(self):
        reload(djstripe_settings)
        reload(fields)

        self.assertTrue(issubclass(fields.JSONField, DjangoJSONField))

    def tearDown(self):
        reload(djstripe_settings)
        reload(fields)
