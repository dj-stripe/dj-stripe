from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict

from django.test import TestCase

from djstripe.enums import EnumMetaClass


class TestEnumMetaClass(TestCase):
    def test_python2_prepare(self):
        # Python 2 hack to ensure __prepare__ is called...
        self.assertEqual(EnumMetaClass.__prepare__(None, None), OrderedDict())
