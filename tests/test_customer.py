import decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from mock import patch

from djstripe.models import Customer, Charge


class TestCustomer(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="patrick", email="patrick@gmail.com")
        self.customer = Customer.objects.create(
            subscriber=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )

    def test_tostring(self):
        self.assertEquals("patrick", str(self.customer))

    @patch("stripe.Customer.retrieve")
    def test_customer_purge_leaves_customer_record(self, CustomerRetrieveMock):
        self.customer.purge()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.card_fingerprint == "")
        self.assertTrue(customer.card_last_4 == "")
        self.assertTrue(customer.card_kind == "")
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    @patch("stripe.Customer.retrieve")
    def test_customer_delete_same_as_purge(self, CustomerRetrieveMock):
        self.customer.delete()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.card_fingerprint == "")
        self.assertTrue(customer.card_last_4 == "")
        self.assertTrue(customer.card_kind == "")
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_change_charge(self):
        self.assertTrue(self.customer.can_charge())

    @patch("stripe.Customer.retrieve")
    def test_cannot_charge(self, CustomerRetrieveMock):
        self.customer.delete()
        self.assertFalse(self.customer.can_charge())

    def test_charge_accepts_only_decimals(self):
        with self.assertRaises(ValueError):
            self.customer.charge(10)

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
            "captured": True,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx"
        }
        obj = self.customer.record_charge("ch_XXXXXX")
        self.assertEquals(Charge.objects.get(stripe_id="ch_XXXXXX").pk, obj.pk)
        self.assertEquals(obj.paid, True)
        self.assertEquals(obj.disputed, False)
        self.assertEquals(obj.refunded, False)
        self.assertEquals(obj.amount_refunded, None)

    @patch("stripe.Charge.retrieve")
    def test_refund_charge(self, RetrieveMock):
        charge = Charge.objects.create(
            stripe_id="ch_XXXXXX",
            customer=self.customer,
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
            "captured": True,
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

    @patch("stripe.Charge.retrieve")
    def test_capture_charge(self, RetrieveMock):
        charge = Charge.objects.create(
            stripe_id="ch_XXXXXX",
            customer=self.customer,
            card_last_4="4323",
            card_kind="Visa",
            amount=decimal.Decimal("10.00"),
            paid=True,
            refunded=False,
            captured=False,
            fee=decimal.Decimal("4.99"),
            disputed=False
        )
        RetrieveMock.return_value.capture.return_value = {
            "id": "ch_XXXXXX",
            "card": {
                "last4": "4323",
                "type": "Visa"
            },
            "amount": 1000,
            "paid": True,
            "refunded": True,
            "captured": True,
            "amount_refunded": 1000,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx"
        }
        charge2 = charge.capture()
        self.assertEquals(charge2.captured, True)

    @patch("stripe.Charge.retrieve")
    def test_refund_charge_object_returned(self, RetrieveMock):
        charge = Charge.objects.create(
            stripe_id="ch_XXXXXX",
            customer=self.customer,
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
            "captured": True,
            "amount_refunded": 1000,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx"
        }
        charge2 = charge.refund()
        self.assertEquals(charge2.refunded, True)
        self.assertEquals(charge2.amount_refunded, decimal.Decimal("10.00"))

    def test_calculate_refund_amount_full_refund(self):
        charge = Charge(
            stripe_id="ch_111111",
            customer=self.customer,
            amount=decimal.Decimal("500.00")
        )
        self.assertEquals(
            charge.calculate_refund_amount(),
            50000
        )

    def test_calculate_refund_amount_partial_refund(self):
        charge = Charge(
            stripe_id="ch_111111",
            customer=self.customer,
            amount=decimal.Decimal("500.00")
        )
        self.assertEquals(
            charge.calculate_refund_amount(amount=decimal.Decimal("300.00")),
            30000
        )

    def test_calculate_refund_above_max_refund(self):
        charge = Charge(
            stripe_id="ch_111111",
            customer=self.customer,
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
            "captured": True,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx"
        }
        self.customer.charge(
            amount=decimal.Decimal("10.00")
        )
        _, kwargs = ChargeMock.call_args
        self.assertEquals(kwargs["amount"], 1000)

    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    def test_charge_passes_extra_arguments(self, ChargeMock, RetrieveMock):
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
            "captured": True,
            "fee": 499,
            "dispute": None,
            "created": 1363911708,
            "customer": "cus_xxxxxxxxxxxxxxx"
        }
        self.customer.charge(
            amount=decimal.Decimal("10.00"),
            capture=True,
            destination='a_stripe_client_id'
        )
        _, kwargs = ChargeMock.call_args
        self.assertEquals(kwargs["capture"], True)
        self.assertEquals(kwargs["destination"], 'a_stripe_client_id')
