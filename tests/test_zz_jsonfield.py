"""
Tests for JSONField

Due to their nature messing with subclassing, these tests must be run last.
"""
from django.contrib.postgres.fields import JSONField as DjangoJSONField
from django.test import TestCase
from django.test.utils import override_settings
from jsonfield import JSONField as UglyJSONField

from djstripe import fields as fields
from djstripe import settings as djstripe_settings

try:
	reload
except NameError:
	from importlib import reload


@override_settings(DJSTRIPE_USE_NATIVE_JSONFIELD=False)
class TestFallbackJSONField(TestCase):
	def test_jsonfield_inheritance(self):
		reload(djstripe_settings)
		reload(fields)

		self.assertTrue(issubclass(fields.JSONField, UglyJSONField))

	def tearDown(self):
		reload(djstripe_settings)
		reload(fields)


@override_settings(DJSTRIPE_USE_NATIVE_JSONFIELD=True)
class TestNativeJSONField(TestCase):
	def test_jsonfield_inheritance(self):
		reload(djstripe_settings)
		reload(fields)

		self.assertTrue(issubclass(fields.JSONField, DjangoJSONField))

	def tearDown(self):
		reload(djstripe_settings)
		reload(fields)
