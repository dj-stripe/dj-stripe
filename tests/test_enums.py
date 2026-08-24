from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from djstripe.enums import DisputeStatus, Enum, TaxIdType


class TestEnumHumanize(TestCase):
    def test_humanize(self):
        class TestEnum(Enum):
            red = _("Red")
            blue = _("Blue")

        self.assertEqual(TestEnum.humanize("red"), _("Red"))

    def test_humanize_unknown_value(self):
        """
        A value Stripe has added but the enum does not know about is returned
        unchanged, rather than raising KeyError. The enums here are maintained
        by hand, so they trail the API, and humanize() is called from __str__.
        """

        class TestEnum(Enum):
            red = _("Red")

        self.assertEqual(TestEnum.humanize("chartreuse"), "chartreuse")


class TestEnumCoverage(TestCase):
    """The enums are hand-maintained; these pin values Stripe has since added."""

    def test_dispute_status_prevented(self):
        self.assertEqual(DisputeStatus.humanize("prevented"), _("Prevented"))

    def test_tax_id_type_gb_vat(self):
        self.assertEqual(TaxIdType.humanize("gb_vat"), _("GB VAT"))
