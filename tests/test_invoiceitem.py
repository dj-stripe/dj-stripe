"""
.. module:: dj-stripe.tests.test_invoiceitem
   :synopsis: dj-stripe InvoiceItem Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from django.test.testcases import TestCase

from djstripe.models import InvoiceItem

from .plan_instances import basic_plan


class InvoiceItemTest(TestCase):

    def test_plan_display(self):
        invoiceitem = InvoiceItem(plan=basic_plan)
        self.assertEqual("Basic Plan", invoiceitem.plan_display())
