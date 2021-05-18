"""
Tests for TextField

Due to their nature messing with subclassing, these tests must be run last.
"""
import sys
from importlib import reload
from unittest import skipUnless

from django.test import TestCase
from django.test.utils import override_settings

from djstripe import fields as fields
from djstripe import settings as djstripe_settings

from django.db.models import TextField as DjangoTextField, CharField as DjangoCharField


@override_settings(DJSTRIPE_USE_NATIVE_TEXTFIELD=False)
class TestCustomizedTextField(TestCase):
    def setUp(self):
        reload(djstripe_settings)
        reload(fields)

    def test_charfield_inheritance(self):
        field = fields.TextField(default="")
        self.assertFalse(isinstance(field, DjangoTextField))
        self.assertTrue(isinstance(field, DjangoCharField))
        self.assertEqual(field.max_length, 500)

    def test_textfield_inheritance(self):
        field = fields.TextField()
        self.assertTrue(isinstance(field, DjangoTextField))
        self.assertFalse(isinstance(field, DjangoCharField))
        self.assertIsNone(field.max_length)


@override_settings(DJSTRIPE_USE_NATIVE_TEXTFIELD=True)
class TestNativeTextField(TestCase):
    def setUp(self):
        reload(djstripe_settings)
        reload(fields)

    def test_textfield_inheritance(self):
        self.assertEqual(fields.TextField, DjangoTextField)
        self.assertFalse(issubclass(fields.TextField, DjangoCharField))
