"""
Tests for JSONField

Due to their nature messing with subclassing, these tests must be run last.
"""
import sys
from unittest import skipUnless

from django.test import TestCase
from django.test.utils import override_settings
from jsonfield import JSONField as UglyJSONField

from djstripe.fields import import_jsonfield

try:
    try:
        from django.db.models import JSONField as DjangoJSONField
    except ImportError:
        from django.contrib.postgres.fields import JSONField as DjangoJSONField
except ImportError:
    pass


@override_settings(DJSTRIPE_USE_NATIVE_JSONFIELD=False)
class TestFallbackJSONField(TestCase):
    def test_jsonfield_inheritance(self):
        self.assertTrue(issubclass(import_jsonfield(), UglyJSONField))


@skipUnless("psycopg2" in sys.modules, "psycopg2 isn't present")
@override_settings(DJSTRIPE_USE_NATIVE_JSONFIELD=True)
class TestNativeJSONField(TestCase):
    def test_jsonfield_inheritance(self):
        self.assertTrue(issubclass(import_jsonfield(), DjangoJSONField))
