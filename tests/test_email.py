import decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

from mock import patch

from djstripe.models import Customer, Account


class EmailReceiptTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="patrick",
                                                         email="patrick@gmail.com")
        self.customer = Customer.objects.create(
            subscriber=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )
        self.account = Account.objects.create()

    @patch("djstripe.models.Account.get_default_account")
    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    def test_email_reciept_renders_amount_properly(self, ChargeMock, RetrieveMock, default_account_mock):
        default_account_mock.return_value = self.account

        ChargeMock.return_value.id = "ch_XXXXX"
        RetrieveMock.return_value = {
            "id": "ch_XXXXXX",
            "card": {
                "last4": "4323",
                "type": "Visa"
            },
            "amount": 40000,
            "amount_refunded": 0,
            "paid": True,
            "refunded": False,
            "captured": True,
            "livemode": True,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx",
            "currency": "usd",
            "status": None,
            "failure_code": None,
            "failure_message": None,
            "fraud_details": {},
            "source": {"id": "asdf", "object": "test"},
            "shipping": None,
        }
        self.customer.charge(
            amount=decimal.Decimal("400.00")
        )
        self.assertTrue("$400.00" in mail.outbox[0].body)
