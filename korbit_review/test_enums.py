from collections import OrderedDict

from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from djstripe.enums import Enum, EnumMetaClass


class TestEnumMetaClass(TestCase):
    def test_python2_prepare(self):
        # Python 2 hack to ensure __prepare__ is called...
        self.assertEqual(EnumMetaClass.__prepare__(None, None), OrderedDict())


class TestEnumHumanize(TestCase):
    def test_humanize(self):
        class TestEnum(Enum):
            red = _("Red")
            blue = _("Blue")

        self.assertEqual(TestEnum.humanize("red"), _("Red"))
