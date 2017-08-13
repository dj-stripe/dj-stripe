"""
Tests for JSONField

Due to their nature messing with subclassing, these tests must be run last.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from django.test import TestCase
from django.test.utils import override_settings

from djstripe import fields as fields
from djstripe import settings as djstripe_settings


try:
    reload
except NameError:
    from importlib import reload


@override_settings(DJSTRIPE_USE_NATIVE_JSONFIELD=False)
class TestFallbackJSONField(TestCase):
    def test_jsonfield_inheritance(self):
        from jsonfield import JSONField
        reload(djstripe_settings)
        reload(fields)

        self.assertTrue(issubclass(fields.StripeJSONField, JSONField))

    def tearDown(self):
        reload(djstripe_settings)
        reload(fields)


@override_settings(DJSTRIPE_USE_NATIVE_JSONFIELD=True)
class TestNativeJSONField(TestCase):
    def test_jsonfield_inheritance(self):
        from django.contrib.postgres.fields import JSONField
        reload(djstripe_settings)
        reload(fields)

        self.assertTrue(issubclass(fields.StripeJSONField, JSONField))

    def tearDown(self):
        reload(djstripe_settings)
        reload(fields)
