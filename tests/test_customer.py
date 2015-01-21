import decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from mock import patch

from djstripe.models import DJStripeCustomer, Charge


class TestCustomer(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="patrick", email="patrick@gmail.com")
        self.djstripecustomer = DJStripeCustomer.objects.create(
            customer=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )

    def test_tostring(self):
        self.assertEquals("patrick", str(self.djstripecustomer))

    @patch("stripe.Customer.retrieve")
    def test_customer_purge_leaves_customer_record(self, CustomerRetrieveMock):
        self.djstripecustomer.purge()
        djstripecustomer = DJStripeCustomer.objects.get(stripe_id=self.djstripecustomer.stripe_id)
        self.assertTrue(djstripecustomer.customer is None)
        self.assertTrue(djstripecustomer.card_fingerprint == "")
        self.assertTrue(djstripecustomer.card_last_4 == "")
        self.assertTrue(djstripecustomer.card_kind == "")
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    @patch("stripe.Customer.retrieve")
    def test_customer_delete_same_as_purge(self, CustomerRetrieveMock):
        self.djstripecustomer.delete()
        djstripecustomer = DJStripeCustomer.objects.get(stripe_id=self.djstripecustomer.stripe_id)
        self.assertTrue(djstripecustomer.customer is None)
        self.assertTrue(djstripecustomer.card_fingerprint == "")
        self.assertTrue(djstripecustomer.card_last_4 == "")
        self.assertTrue(djstripecustomer.card_kind == "")
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_change_charge(self):
        self.assertTrue(self.djstripecustomer.can_charge())

    @patch("stripe.Customer.retrieve")
    def test_cannot_charge(self, CustomerRetrieveMock):
        self.djstripecustomer.delete()
        self.assertFalse(self.djstripecustomer.can_charge())

    def test_charge_accepts_only_decimals(self):
        with self.assertRaises(ValueError):
            self.djstripecustomer.charge(10)

    @patch("stripe.Charge.retrieve")
    def test_record_charge(self, RetrieveMock):
        RetrieveMock.return_value = {
            "id": "ch_XXXXXX",
            "card": {
                "last4": "4323",
                "type": "Visa"
            },
            "amount": 1000,
            "paid": True,
            "refunded": False,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx"
        }
        obj = self.djstripecustomer.record_charge("ch_XXXXXX")
        self.assertEquals(Charge.objects.get(stripe_id="ch_XXXXXX").pk, obj.pk)
        self.assertEquals(obj.paid, True)
        self.assertEquals(obj.disputed, False)
        self.assertEquals(obj.refunded, False)
        self.assertEquals(obj.amount_refunded, None)

    @patch("stripe.Charge.retrieve")
    def test_refund_charge(self, RetrieveMock):
        charge = Charge.objects.create(
            stripe_id="ch_XXXXXX",
            djstripecustomer=self.djstripecustomer,
            card_last_4="4323",
            card_kind="Visa",
            amount=decimal.Decimal("10.00"),
            paid=True,
            refunded=False,
            fee=decimal.Decimal("4.99"),
            disputed=False
        )
        RetrieveMock.return_value.refund.return_value = {
            "id": "ch_XXXXXX",
            "card": {
                "last4": "4323",
                "type": "Visa"
            },
            "amount": 1000,
            "paid": True,
            "refunded": True,
            "amount_refunded": 1000,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx"
        }
        charge.refund()
        charge2 = Charge.objects.get(stripe_id="ch_XXXXXX")
        self.assertEquals(charge2.refunded, True)
        self.assertEquals(charge2.amount_refunded, decimal.Decimal("10.00"))

    def test_calculate_refund_amount_full_refund(self):
        charge = Charge(
            stripe_id="ch_111111",
            djstripecustomer=self.djstripecustomer,
            amount=decimal.Decimal("500.00")
        )
        self.assertEquals(
            charge.calculate_refund_amount(),
            50000
        )

    def test_calculate_refund_amount_partial_refund(self):
        charge = Charge(
            stripe_id="ch_111111",
            djstripecustomer=self.djstripecustomer,
            amount=decimal.Decimal("500.00")
        )
        self.assertEquals(
            charge.calculate_refund_amount(amount=decimal.Decimal("300.00")),
            30000
        )

    def test_calculate_refund_above_max_refund(self):
        charge = Charge(
            stripe_id="ch_111111",
            djstripecustomer=self.djstripecustomer,
            amount=decimal.Decimal("500.00")
        )
        self.assertEquals(
            charge.calculate_refund_amount(amount=decimal.Decimal("600.00")),
            50000
        )

    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    def test_charge_converts_dollars_into_cents(self, ChargeMock, RetrieveMock):
        ChargeMock.return_value.id = "ch_XXXXX"
        RetrieveMock.return_value = {
            "id": "ch_XXXXXX",
            "card": {
                "last4": "4323",
                "type": "Visa"
            },
            "amount": 1000,
            "paid": True,
            "refunded": False,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx"
        }
        self.djstripecustomer.charge(
            amount=decimal.Decimal("10.00")
        )
        _, kwargs = ChargeMock.call_args
        self.assertEquals(kwargs["amount"], 1000)
