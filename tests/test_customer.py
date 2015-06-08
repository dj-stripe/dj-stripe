import decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from mock import patch, PropertyMock, MagicMock
import stripe

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
    def test_customer_purge_leaves_customer_record(self, customer_retrieve_fake):
        self.customer.purge()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.card_fingerprint == "")
        self.assertTrue(customer.card_last_4 == "")
        self.assertTrue(customer.card_kind == "")
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    @patch("stripe.Customer.retrieve")
    def test_customer_delete_same_as_purge(self, customer_retrieve_fake):
        self.customer.delete()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.card_fingerprint == "")
        self.assertTrue(customer.card_last_4 == "")
        self.assertTrue(customer.card_kind == "")
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    @patch("stripe.Customer.retrieve")
    def test_customer_purge_raises_customer_exception(self, customer_retrieve_mock):
        customer_retrieve_mock.side_effect = stripe.InvalidRequestError("No such customer:", "blah")

        self.customer.purge()
        customer = Customer.objects.get(stripe_id=self.customer.stripe_id)
        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.card_fingerprint == "")
        self.assertTrue(customer.card_last_4 == "")
        self.assertTrue(customer.card_kind == "")
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

        customer_retrieve_mock.assert_called_once_with(self.customer.stripe_id)

    @patch("stripe.Customer.retrieve")
    def test_customer_delete_raises_unexpected_exception(self, customer_retrieve_mock):
        customer_retrieve_mock.side_effect = stripe.InvalidRequestError("Unexpected Exception", "blah")

        with self.assertRaisesMessage(stripe.InvalidRequestError, "Unexpected Exception"):
            self.customer.purge()

        customer_retrieve_mock.assert_called_once_with(self.customer.stripe_id)

    def test_change_charge(self):
        self.assertTrue(self.customer.can_charge())

    @patch("stripe.Customer.retrieve")
    def test_cannot_charge(self, customer_retrieve_fake):
        self.customer.delete()
        self.assertFalse(self.customer.can_charge())

    def test_charge_accepts_only_decimals(self):
        with self.assertRaises(ValueError):
            self.customer.charge(10)

    @patch("stripe.Charge.retrieve")
    def test_record_charge(self, charge_retrieve_mock):
        charge_retrieve_mock.return_value = {
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
    def test_refund_charge(self, charge_retrieve_mock):
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
        charge_retrieve_mock.return_value.refund.return_value = {
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
    def test_capture_charge(self, charge_retrieve_mock):
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
        charge_retrieve_mock.return_value.capture.return_value = {
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
    def test_refund_charge_object_returned(self, charge_retrieve_mock):
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
        charge_retrieve_mock.return_value.refund.return_value = {
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
    def test_charge_converts_dollars_into_cents(self, charge_create_mock, charge_retrieve_mock):
        charge_create_mock.return_value.id = "ch_XXXXX"
        charge_retrieve_mock.return_value = {
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
        _, kwargs = charge_create_mock.call_args
        self.assertEquals(kwargs["amount"], 1000)

    @patch("stripe.Charge.retrieve")
    @patch("stripe.Charge.create")
    def test_charge_passes_extra_arguments(self, charge_create_mock, charge_retrieve_mock):
        charge_create_mock.return_value.id = "ch_XXXXX"
        charge_retrieve_mock.return_value = {
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
        _, kwargs = charge_create_mock.call_args
        self.assertEquals(kwargs["capture"], True)
        self.assertEquals(kwargs["destination"], 'a_stripe_client_id')

    @patch("djstripe.models.djstripe_settings.trial_period_for_subscriber_callback", return_value="donkey")
    @patch("stripe.Customer.create", return_value=PropertyMock(id="cus_xxx1234567890"))
    def test_create_trial_callback(self, customer_create_mock, callback_mock):
        user = get_user_model().objects.create_user(username="test", email="test@gmail.com")
        Customer.create(user)

        customer_create_mock.assert_called_once_with(email=user.email)
        callback_mock.assert_called_once_with(user)

    @patch("djstripe.models.Customer.subscribe")
    @patch("djstripe.models.djstripe_settings.DEFAULT_PLAN", new_callable=PropertyMock, return_value="schreck")
    @patch("djstripe.models.djstripe_settings.trial_period_for_subscriber_callback", return_value="donkey")
    @patch("stripe.Customer.create", return_value=PropertyMock(id="cus_xxx1234567890"))
    def test_create_default_plan(self, customer_create_mock, callback_mock, default_plan_fake, subscribe_mock):
        user = get_user_model().objects.create_user(username="test", email="test@gmail.com")
        Customer.create(user)

        customer_create_mock.assert_called_once_with(email=user.email)
        callback_mock.assert_called_once_with(user)
        subscribe_mock.assert_called_once_with(plan=default_plan_fake, trial_days="donkey")

    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_update_card(self, customer_stripe_customer_mock):
        customer_stripe_customer_mock.return_value = PropertyMock(active_card=PropertyMock(fingerprint="test_fingerprint",
                                                                                           last4="1234", type="test_type"))

        self.customer.update_card("test")

        self.assertEqual("test_fingerprint", self.customer.card_fingerprint)
        self.assertEqual("1234", self.customer.card_last_4)
        self.assertEqual("test_type", self.customer.card_kind)

    @patch("stripe.Invoice.create")
    def test_send_invoice_success(self, invoice_create_mock):
        return_status = self.customer.send_invoice()
        self.assertTrue(return_status)

        invoice_create_mock.assert_called_once_with(customer=self.customer.stripe_id)

    @patch("stripe.Invoice.create")
    def test_send_invoice_failure(self, invoice_create_mock):
        invoice_create_mock.side_effect = stripe.InvalidRequestError("Invoice creation failed.", "blah")

        return_status = self.customer.send_invoice()
        self.assertFalse(return_status)

        invoice_create_mock.assert_called_once_with(customer=self.customer.stripe_id)

    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock)
    def test_sync_active_card(self, stripe_customer_mock):
        stripe_customer_mock.return_value = PropertyMock(active_card=PropertyMock(fingerprint="cherry",
                                                                                  last4="4429", type="apple"))
        self.customer.sync()
        self.assertEqual("cherry", self.customer.card_fingerprint)
        self.assertEqual("4429", self.customer.card_last_4)
        self.assertEqual("apple", self.customer.card_kind)

    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock,
           return_value=PropertyMock(active_card=None))
    def test_sync_no_card(self, stripe_customer_mock):
        self.customer.sync()
        self.assertEqual("YYYYYYYY", self.customer.card_fingerprint)
        self.assertEqual("2342", self.customer.card_last_4)
        self.assertEqual("Visa", self.customer.card_kind)

    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock,
           return_value=PropertyMock(invoices=MagicMock(return_value=PropertyMock(data=["apple", "orange", "pear"]))))
    def test_sync_invoices(self, stripe_customer_mock, sync_from_stripe_data_mock):
        self.customer.sync_invoices()

        sync_from_stripe_data_mock.assert_any_call("apple", send_receipt=False)
        sync_from_stripe_data_mock.assert_any_call("orange", send_receipt=False)
        sync_from_stripe_data_mock.assert_any_call("pear", send_receipt=False)

        self.assertEqual(3, sync_from_stripe_data_mock.call_count)

    @patch("djstripe.models.Invoice.sync_from_stripe_data")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock,
       return_value=PropertyMock(invoices=MagicMock(return_value=PropertyMock(data=[]))))
    def test_sync_invoices_none(self, stripe_customer_mock, sync_from_stripe_data_mock):
        self.customer.sync_invoices()

        self.assertFalse(sync_from_stripe_data_mock.called)

    @patch("djstripe.models.Customer.record_charge")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock,
           return_value=PropertyMock(charges=MagicMock(return_value=PropertyMock(data=[PropertyMock(id="herbst"), 
                                                                                       PropertyMock(id="winter"), 
                                                                                       PropertyMock(id="fruehling"), 
                                                                                       PropertyMock(id="sommer")]))))
    def test_sync_charges(self, stripe_customer_mock, record_charge_mock):
        self.customer.sync_charges()

        record_charge_mock.assert_any_call("herbst")
        record_charge_mock.assert_any_call("winter")
        record_charge_mock.assert_any_call("fruehling")
        record_charge_mock.assert_any_call("sommer")

        self.assertEqual(4, record_charge_mock.call_count)

    @patch("djstripe.models.Customer.record_charge")
    @patch("djstripe.models.Customer.stripe_customer", new_callable=PropertyMock,
           return_value=PropertyMock(charges=MagicMock(return_value=PropertyMock(data=[]))))
    def test_sync_charges_none(self, stripe_customer_mock, record_charge_mock):
        self.customer.sync_charges()

        self.assertFalse(record_charge_mock.called)