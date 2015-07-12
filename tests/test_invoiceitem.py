"""
.. module:: dj-stripe.tests.test_invoiceitem
   :synopsis: dj-stripe InvoiceItem Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from django.test.testcases import TestCase

from djstripe.models import InvoiceItem

from .plan_instances import basic_plan
from .plan_instances import test


class InvoiceItemTest(TestCase):

    def test_plan_display(self):
        invoiceitem = InvoiceItem(plan=basic_plan)
        self.assertEqual("Basic Plan", invoiceitem.plan_display())

    def test_tostring(self):
        invoiceitem = InvoiceItem(plan=test, amount=50, stripe_id='inv_xxxxxxxx123456')
        self.assertEquals("<amount=50, plan=<test, stripe_id=test>, stripe_id=inv_xxxxxxxx123456>", str(invoiceitem))
