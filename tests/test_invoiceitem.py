"""
.. module:: dj-stripe.tests.test_invoiceitem
   :synopsis: dj-stripe InvoiceItem Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from django.test.testcases import TestCase

from djstripe.models import InvoiceItem


class InvoiceItemTest(TestCase):

    def test_plan_display(self):
        invoiceitem = InvoiceItem(plan="test")
        self.assertEqual("Test Plan 1", invoiceitem.plan_display())
