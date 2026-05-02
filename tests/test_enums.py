from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from djstripe.enums import Enum


class TestEnumHumanize(TestCase):
    def test_humanize(self):
        class TestEnum(Enum):
            red = _("Red")
            blue = _("Blue")

        self.assertEqual(TestEnum.humanize("red"), _("Red"))
