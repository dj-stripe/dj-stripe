import decimal

from django.core import mail
from django.test import TestCase

from mock import patch

from ..models import Customer
from ..settings import User


class EmailReceiptTest(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(username="patrick")
        self.customer = Customer.objects.create(
            user=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )
    
    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    def test_email_reciept_renders_amount_properly(self, ChargeMock, RetrieveMock):  # pylint: disable=C0301
        ChargeMock.return_value.id = "ch_XXXXX"
        RetrieveMock.return_value = {
            "id": "ch_XXXXXX",
            "card": {
                "last4": "4323",
                "type": "Visa"
            },
            "amount": 40000,
            "paid": True,
            "refunded": False,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx"
        }
        self.customer.charge(
            amount=decimal.Decimal("400.00")
        )
        self.assertTrue("$400.00" in mail.outbox[0].body)
