"""
.. module:: dj-stripe.tests.test_email
   :synopsis: dj-stripe Email Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy
import decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

from mock import patch

from djstripe.models import Customer, Account

from tests import FAKE_CHARGE, FAKE_CUSTOMER


class EmailReceiptTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        self.customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")
        self.account = Account.objects.create()

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    def test_email_reciept_renders_amount_properly(self, charge_create_mock, charge_retrieve_mock, default_account_mock):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": None})

        charge_create_mock.return_value = fake_charge_copy
        charge_retrieve_mock.return_value = fake_charge_copy

        self.customer.charge(amount=decimal.Decimal("22.00"))
        self.assertTrue("$22.00" in mail.outbox[0].body)
