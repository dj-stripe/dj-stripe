"""
Customer Model Tests.
"""
import decimal
from copy import deepcopy
from unittest.mock import ANY, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from stripe.error import InvalidRequestError

from djstripe import settings as djstripe_settings
from djstripe.exceptions import MultipleSubscriptionException
from djstripe.models import (
    Card,
    Charge,
    Coupon,
    Customer,
    DjstripePaymentMethod,
    IdempotencyKey,
    Invoice,
    PaymentMethod,
    Plan,
    Subscription,
)
from djstripe.settings import STRIPE_SECRET_KEY

from . import (
    FAKE_ACCOUNT,
    FAKE_BALANCE_TRANSACTION,
    FAKE_CARD,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CARD_V,
    FAKE_CHARGE,
    FAKE_COUPON,
    FAKE_CUSTOMER,
    FAKE_CUSTOMER_II,
    FAKE_CUSTOMER_III,
    FAKE_CUSTOMER_IV,
    FAKE_DISCOUNT_CUSTOMER,
    FAKE_INVOICE,
    FAKE_INVOICE_III,
    FAKE_INVOICEITEM,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PAYMENT_METHOD_I,
    FAKE_PLAN,
    FAKE_PRODUCT,
    FAKE_SOURCE,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_II,
    FAKE_UPCOMING_INVOICE,
    IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    AssertStripeFksMixin,
    StripeList,
    datetime_to_unix,
    default_account,
)


class TestCustomer(AssertStripeFksMixin, TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

        self.payment_method, _ = DjstripePaymentMethod._get_or_create_source(
            FAKE_CARD, "card"
        )
        self.card = self.payment_method.resolve()

        self.customer.default_source = self.payment_method
        self.customer.save()

        self.account = default_account()

    def test_str(self):
        self.assertEqual(str(self.customer), self.user.email)
        self.customer.subscriber.email = ""
        self.assertEqual(str(self.customer), self.customer.id)
        self.customer.subscriber = None
        self.assertEqual(
            str(self.customer), "{id} (deleted)".format(id=self.customer.id)
        )

    def test_balance(self):
        self.assertEqual(self.customer.balance, 0)
        self.assertEqual(self.customer.credits, 0)

        self.customer.balance = 1000
        self.assertEqual(self.customer.balance, 1000)
        self.assertEqual(self.customer.credits, 0)
        self.assertEqual(self.customer.pending_charges, 1000)

        self.customer.balance = -1000
        self.assertEqual(self.customer.balance, -1000)
        self.assertEqual(self.customer.credits, 1000)
        self.assertEqual(self.customer.pending_charges, 0)

    def test_customer_dashboard_url(self):
        expected_url = "https://dashboard.stripe.com/test/customers/{}".format(
            self.customer.id
        )
        self.assertEqual(self.customer.get_stripe_dashboard_url(), expected_url)

        self.customer.livemode = True
        expected_url = "https://dashboard.stripe.com/customers/{}".format(
            self.customer.id
        )
        self.assertEqual(self.customer.get_stripe_dashboard_url(), expected_url)

        unsaved_customer = Customer()
        self.assertEqual(unsaved_customer.get_stripe_dashboard_url(), "")

    def test_customer_sync_unsupported_source(self):
        fake_customer = deepcopy(FAKE_CUSTOMER_II)
        fake_customer["default_source"]["object"] = fake_customer["sources"]["data"][0][
            "object"
        ] = "fish"

        user = get_user_model().objects.create_user(
            username="test_user_sync_unsupported_source"
        )
        synced_customer = fake_customer.create_for_user(user)
        self.assertEqual(0, synced_customer.legacy_cards.count())
        self.assertEqual(0, synced_customer.sources.count())
        self.assertEqual(
            synced_customer.default_source,
            DjstripePaymentMethod.objects.get(id=fake_customer["default_source"]["id"]),
        )

    def test_customer_sync_has_subscriber_metadata(self):
        user = get_user_model().objects.create(username="test_metadata", id=12345)

        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["id"] = "cus_sync_has_subscriber_metadata"
        fake_customer["metadata"] = {"djstripe_subscriber": "12345"}
        customer = Customer.sync_from_stripe_data(fake_customer)

        self.assertEqual(customer.subscriber, user)
        self.assertEqual(customer.metadata, {"djstripe_subscriber": "12345"})

    def test_customer_sync_has_subscriber_metadata_disabled(self):
        user = get_user_model().objects.create(
            username="test_metadata_disabled", id=98765
        )

        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["id"] = "cus_test_metadata_disabled"
        fake_customer["metadata"] = {"djstripe_subscriber": "98765"}
        with patch(
            "djstripe.settings.SUBSCRIBER_CUSTOMER_KEY", return_value="", autospec=True
        ):
            customer = Customer.sync_from_stripe_data(fake_customer)

        self.assertNotEqual(customer.subscriber, user)
        self.assertNotEqual(customer.subscriber_id, 98765)

        self.assert_fks(
            customer,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
            },
        )

    def test_customer_sync_has_bad_subscriber_metadata(self):
        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["id"] = "cus_sync_has_bad_subscriber_metadata"
        fake_customer["metadata"] = {"djstripe_subscriber": "does_not_exist"}
        customer = Customer.sync_from_stripe_data(fake_customer)

        self.assertEqual(customer.subscriber, None)
        self.assertEqual(customer.metadata, {"djstripe_subscriber": "does_not_exist"})

        self.assert_fks(
            customer,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
            },
        )

    @patch("stripe.Customer.create", autospec=True)
    def test_customer_create_metadata_disabled(self, customer_mock):
        user = get_user_model().objects.create_user(
            username="test_user_create_metadata_disabled"
        )

        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["id"] = "cus_test_create_metadata_disabled"
        customer_mock.return_value = fake_customer

        djstripe_settings.SUBSCRIBER_CUSTOMER_KEY = ""
        customer = Customer.create(user)
        djstripe_settings.SUBSCRIBER_CUSTOMER_KEY = "djstripe_subscriber"

        customer_mock.assert_called_once_with(
            api_key=STRIPE_SECRET_KEY,
            email="",
            idempotency_key=None,
            metadata={},
            stripe_account=None,
        )

        self.assertEqual(customer.metadata, None)

        self.assert_fks(
            customer,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.default_source",
            },
        )

    @patch(
        "stripe.Card.retrieve",
        return_value=FAKE_CUSTOMER_II["default_source"],
        autospec=True,
    )
    def test_customer_sync_non_local_card(self, card_retrieve_mock):
        fake_customer = deepcopy(FAKE_CUSTOMER_II)
        fake_customer["id"] = fake_customer["sources"]["data"][0][
            "customer"
        ] = "cus_test_sync_non_local_card"

        user = get_user_model().objects.create_user(
            username="test_user_sync_non_local_card"
        )
        customer = fake_customer.create_for_user(user)

        self.assertEqual(customer.sources.count(), 0)
        self.assertEqual(customer.legacy_cards.count(), 1)
        self.assertEqual(
            customer.default_source.id, fake_customer["default_source"]["id"]
        )

    @patch(
        "stripe.BankAccount.retrieve",
        return_value=FAKE_CUSTOMER_IV["default_source"],
        autospec=True,
    )
    def test_customer_sync_bank_account_source(self, bank_account_retrieve_mock):
        fake_customer = deepcopy(FAKE_CUSTOMER_IV)
        user = get_user_model().objects.create_user(
            username="test_user_sync_bank_account_source"
        )
        customer = fake_customer.create_for_user(user)

        self.assertEqual(customer.sources.count(), 0)
        self.assertEqual(customer.legacy_cards.count(), 0)
        self.assertEqual(customer.bank_account.count(), 1)
        self.assertEqual(
            customer.default_source.id, fake_customer["default_source"]["id"]
        )

        self.assert_fks(
            customer,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
            },
        )

    @patch("stripe.Customer.create", autospec=True)
    def test_customer_sync_no_sources(self, customer_mock):
        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["id"] = "cus_test_sync_no_sources"
        fake_customer["default_source"] = None
        fake_customer["sources"] = None
        customer_mock.return_value = fake_customer

        user = get_user_model().objects.create_user(
            username="test_user_sync_non_local_card"
        )
        customer = Customer.create(user)
        self.assertEqual(
            customer_mock.call_args_list[0][1].get("metadata"),
            {"djstripe_subscriber": user.pk},
        )

        self.assertEqual(customer.sources.count(), 0)
        self.assertEqual(customer.legacy_cards.count(), 0)
        self.assertEqual(customer.default_source, None)

        self.assert_fks(
            customer,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.default_source",
            },
        )

    def test_customer_sync_default_source_string(self):
        Customer.objects.all().delete()
        Card.objects.all().delete()
        customer_fake = deepcopy(FAKE_CUSTOMER)
        customer_fake["default_source"] = customer_fake["sources"]["data"][0][
            "id"
        ] = "card_sync_source_string"
        customer = Customer.sync_from_stripe_data(customer_fake)
        self.assertEqual(customer.default_source.id, customer_fake["default_source"])
        self.assertEqual(customer.legacy_cards.count(), 2)
        self.assertEqual(len(list(customer.customer_payment_methods)), 2)

        self.assert_fks(
            customer,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
            },
        )

    @patch("stripe.Customer.retrieve", autospec=True)
    def test_customer_purge_leaves_customer_record(self, customer_retrieve_fake):
        self.customer.purge()
        customer = Customer.objects.get(id=self.customer.id)

        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.default_source is None)
        self.assertTrue(not customer.legacy_cards.all())
        self.assertTrue(not customer.sources.all())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    @patch("stripe.Customer.create", autospec=True)
    def test_customer_purge_detaches_sources(self, customer_api_create_fake):
        fake_customer = deepcopy(FAKE_CUSTOMER_III)
        customer_api_create_fake.return_value = fake_customer

        user = get_user_model().objects.create_user(
            username="blah", email=FAKE_CUSTOMER_III["email"]
        )

        Customer.get_or_create(user)
        customer = Customer.sync_from_stripe_data(deepcopy(FAKE_CUSTOMER_III))

        self.assertIsNotNone(customer.default_source)
        self.assertNotEqual(customer.sources.count(), 0)

        with patch("stripe.Customer.retrieve", autospec=True), patch(
            "stripe.Source.retrieve", return_value=deepcopy(FAKE_SOURCE), autospec=True
        ):
            customer.purge()

        self.assertIsNone(customer.default_source)
        self.assertEqual(customer.sources.count(), 0)

    @patch(
        "stripe.Customer.create", return_value=deepcopy(FAKE_CUSTOMER_II), autospec=True
    )
    def test_customer_purge_deletes_idempotency_key(self, customer_api_create_fake):
        # We need to call Customer.get_or_create (which setUp doesn't)
        # to get an idempotency key
        user = get_user_model().objects.create_user(
            username="blah", email=FAKE_CUSTOMER_II["email"]
        )
        idempotency_key_action = "customer:create:{}".format(user.pk)
        self.assertFalse(
            IdempotencyKey.objects.filter(action=idempotency_key_action).exists()
        )

        customer, created = Customer.get_or_create(user)
        self.assertTrue(
            IdempotencyKey.objects.filter(action=idempotency_key_action).exists()
        )

        with patch("stripe.Customer.retrieve", autospec=True):
            customer.purge()

        self.assertFalse(
            IdempotencyKey.objects.filter(action=idempotency_key_action).exists()
        )

    @patch("stripe.Customer.retrieve", autospec=True)
    def test_customer_delete_same_as_purge(self, customer_retrieve_fake):
        self.customer.delete()
        customer = Customer.objects.get(id=self.customer.id)

        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.default_source is None)
        self.assertTrue(not customer.legacy_cards.all())
        self.assertTrue(not customer.sources.all())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    @patch("stripe.Customer.retrieve", autospec=True)
    def test_customer_purge_raises_customer_exception(self, customer_retrieve_mock):
        customer_retrieve_mock.side_effect = InvalidRequestError(
            "No such customer:", "blah"
        )

        self.customer.purge()
        customer = Customer.objects.get(id=self.customer.id)
        self.assertTrue(customer.subscriber is None)
        self.assertTrue(customer.default_source is None)
        self.assertTrue(not customer.legacy_cards.all())
        self.assertTrue(not customer.sources.all())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

        customer_retrieve_mock.assert_called_with(
            id=self.customer.id,
            api_key=STRIPE_SECRET_KEY,
            expand=["default_source"],
            stripe_account=None,
        )
        self.assertEqual(3, customer_retrieve_mock.call_count)

    @patch("stripe.Customer.retrieve", autospec=True)
    def test_customer_delete_raises_unexpected_exception(self, customer_retrieve_mock):
        customer_retrieve_mock.side_effect = InvalidRequestError(
            "Unexpected Exception", "blah"
        )

        with self.assertRaisesMessage(InvalidRequestError, "Unexpected Exception"):
            self.customer.purge()

        customer_retrieve_mock.assert_called_once_with(
            id=self.customer.id,
            api_key=STRIPE_SECRET_KEY,
            expand=["default_source"],
            stripe_account=None,
        )

    def test_can_charge(self):
        self.assertTrue(self.customer.can_charge())

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_add_card_set_default_true(self, customer_retrieve_mock):
        self.customer.add_card(FAKE_CARD["id"])
        self.customer.add_card(FAKE_CARD_V["id"])

        self.assertEqual(2, Card.objects.count())
        self.assertEqual(FAKE_CARD_V["id"], self.customer.default_source.id)

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_add_card_set_default_false(self, customer_retrieve_mock):
        self.customer.add_card(FAKE_CARD["id"], set_default=False)
        self.customer.add_card(FAKE_CARD_V["id"], set_default=False)

        self.assertEqual(2, Card.objects.count())
        self.assertEqual(FAKE_CARD["id"], self.customer.default_source.id)

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_add_card_set_default_false_with_single_card_still_becomes_default(
        self, customer_retrieve_mock
    ):
        self.customer.add_card(FAKE_CARD["id"], set_default=False)

        self.assertEqual(2, Card.objects.count())
        self.assertEqual(FAKE_CARD["id"], self.customer.default_source.id)

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch("stripe.PaymentMethod.attach", return_value=deepcopy(FAKE_PAYMENT_METHOD_I))
    def test_add_payment_method_obj(self, attach_mock, customer_retrieve_mock):
        self.assertEqual(
            self.customer.payment_methods.filter(
                id=FAKE_PAYMENT_METHOD_I["id"]
            ).count(),
            0,
        )

        payment_method = PaymentMethod.sync_from_stripe_data(FAKE_PAYMENT_METHOD_I)
        payment_method = self.customer.add_payment_method(payment_method)

        self.assertEqual(payment_method.customer.id, self.customer.id)

        self.assertEqual(
            self.customer.payment_methods.filter(
                id=FAKE_PAYMENT_METHOD_I["id"]
            ).count(),
            1,
        )

        self.assertEqual(
            self.customer.payment_methods.filter(
                id=FAKE_PAYMENT_METHOD_I["id"]
            ).first(),
            self.customer.default_payment_method,
        )

        self.assertEqual(
            self.customer.default_payment_method.id,
            self.customer.invoice_settings["default_payment_method"],
        )

        self.assert_fks(self.customer, expected_blank_fks={"djstripe.Customer.coupon"})

    @patch("stripe.Customer.retrieve", autospec=True)
    @patch("stripe.PaymentMethod.attach", return_value=deepcopy(FAKE_PAYMENT_METHOD_I))
    def test_add_payment_method_set_default_true(
        self, attach_mock, customer_retrieve_mock
    ):
        # clear default source so we can check can_charge()
        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["default_source"] = None
        customer_retrieve_mock.return_value = fake_customer

        self.customer.default_source = None
        self.customer.save()

        self.assertEqual(
            self.customer.payment_methods.filter(
                id=FAKE_PAYMENT_METHOD_I["id"]
            ).count(),
            0,
        )

        payment_method = self.customer.add_payment_method(FAKE_PAYMENT_METHOD_I["id"])

        self.assertEqual(payment_method.customer.id, self.customer.id)

        self.assertEqual(
            self.customer.payment_methods.filter(
                id=FAKE_PAYMENT_METHOD_I["id"]
            ).count(),
            1,
        )

        self.assertEqual(
            self.customer.payment_methods.filter(
                id=FAKE_PAYMENT_METHOD_I["id"]
            ).first(),
            self.customer.default_payment_method,
        )

        self.assertEqual(
            self.customer.default_payment_method.id,
            self.customer.invoice_settings["default_payment_method"],
        )

        self.assertTrue(
            self.customer.can_charge(),
            "Expect to be able to charge since we've set a default_payment_method",
        )

        self.assert_fks(
            self.customer,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_source",
            },
        )

    @patch("stripe.Customer.retrieve", autospec=True)
    @patch("stripe.PaymentMethod.attach", return_value=deepcopy(FAKE_PAYMENT_METHOD_I))
    def test_add_payment_method_set_default_false(
        self, attach_mock, customer_retrieve_mock
    ):
        # clear default source so we can check can_charge()
        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["default_source"] = None
        customer_retrieve_mock.return_value = fake_customer

        self.customer.default_source = None
        self.customer.save()

        self.assertEqual(
            self.customer.payment_methods.filter(
                id=FAKE_PAYMENT_METHOD_I["id"]
            ).count(),
            0,
        )

        payment_method = self.customer.add_payment_method(
            FAKE_PAYMENT_METHOD_I["id"], set_default=False
        )

        self.assertEqual(payment_method.customer.id, self.customer.id)

        self.assertEqual(
            self.customer.payment_methods.filter(
                id=FAKE_PAYMENT_METHOD_I["id"]
            ).count(),
            1,
        )

        self.assertFalse(
            self.customer.can_charge(),
            "Expect not to be able to charge since we've not set a "
            "default_payment_method",
        )

        self.assert_fks(
            self.customer,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.default_source",
            },
        )

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_cannot_charge(self, customer_retrieve_fake):
        self.customer.delete()
        self.assertFalse(self.customer.can_charge())

    def test_charge_accepts_only_decimals(self):
        with self.assertRaises(ValueError):
            self.customer.charge(10)

    @patch("stripe.Coupon.retrieve", return_value=deepcopy(FAKE_COUPON), autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_add_coupon_by_id(self, customer_retrieve_mock, coupon_retrieve_mock):
        self.assertEqual(self.customer.coupon, None)
        self.customer.add_coupon(FAKE_COUPON["id"])
        customer_retrieve_mock.assert_called_once_with(
            api_key=STRIPE_SECRET_KEY,
            expand=["default_source"],
            id=FAKE_CUSTOMER["id"],
            stripe_account=None,
        )

    @patch("stripe.Coupon.retrieve", return_value=deepcopy(FAKE_COUPON), autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_add_coupon_by_object(self, customer_retrieve_mock, coupon_retrieve_mock):
        self.assertEqual(self.customer.coupon, None)
        coupon = Coupon.sync_from_stripe_data(FAKE_COUPON)
        fake_discount = deepcopy(FAKE_DISCOUNT_CUSTOMER)

        def fake_customer_save(self, *args, **kwargs):
            # fake the api coupon update behaviour
            coupon = self.pop("coupon", None)
            if coupon:
                self["discount"] = fake_discount
            else:
                self["discount"] = None

            return self

        with patch("tests.CustomerDict.save", new=fake_customer_save):
            self.customer.add_coupon(coupon)

        customer_retrieve_mock.assert_called_once_with(
            api_key=STRIPE_SECRET_KEY,
            expand=["default_source"],
            id=FAKE_CUSTOMER["id"],
            stripe_account=None,
        )

        self.customer.refresh_from_db()

        self.assert_fks(
            self.customer,
            expected_blank_fks={"djstripe.Customer.default_payment_method"},
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", autospec=True)
    @patch("stripe.PaymentIntent.retrieve", autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    def test_refund_charge(
        self,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        fake_charge_no_invoice = deepcopy(FAKE_CHARGE)
        fake_charge_no_invoice.update({"invoice": None})

        charge_retrieve_mock.return_value = fake_charge_no_invoice

        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)
        fake_payment_intent.update({"invoice": None})

        payment_intent_retrieve_mock.return_value = fake_payment_intent

        charge, created = Charge._get_or_create_from_stripe_object(
            fake_charge_no_invoice
        )
        self.assertTrue(created)

        self.assert_fks(
            charge,
            expected_blank_fks={
                "djstripe.Account.branding_logo",
                "djstripe.Account.branding_icon",
                "djstripe.Charge.dispute",
                "djstripe.Charge.latest_invoice (related name)",
                "djstripe.Charge.latest_upcominginvoice (related name)",
                "djstripe.Charge.invoice",
                "djstripe.Charge.transfer",
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.PaymentIntent.upcominginvoice (related name)",
            },
        )

        charge.refund()

        refunded_charge, created2 = Charge._get_or_create_from_stripe_object(
            fake_charge_no_invoice
        )
        self.assertFalse(created2)

        self.assertEqual(refunded_charge.refunded, True)
        self.assertEqual(refunded_charge.amount_refunded, decimal.Decimal("20.00"))

        self.assert_fks(
            refunded_charge,
            expected_blank_fks={
                "djstripe.Account.branding_logo",
                "djstripe.Account.branding_icon",
                "djstripe.Charge.dispute",
                "djstripe.Charge.latest_invoice (related name)",
                "djstripe.Charge.latest_upcominginvoice (related name)",
                "djstripe.Charge.invoice",
                "djstripe.Charge.transfer",
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.PaymentIntent.upcominginvoice (related name)",
            },
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", autospec=True)
    @patch("stripe.PaymentIntent.retrieve", autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    def test_refund_charge_object_returned(
        self,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        fake_charge_no_invoice = deepcopy(FAKE_CHARGE)
        fake_charge_no_invoice.update({"invoice": None})

        charge_retrieve_mock.return_value = fake_charge_no_invoice

        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)
        fake_payment_intent.update({"invoice": None})

        payment_intent_retrieve_mock.return_value = fake_payment_intent

        charge, created = Charge._get_or_create_from_stripe_object(
            fake_charge_no_invoice
        )
        self.assertTrue(created)

        self.assert_fks(
            charge,
            expected_blank_fks={
                "djstripe.Account.branding_logo",
                "djstripe.Account.branding_icon",
                "djstripe.Charge.dispute",
                "djstripe.Charge.latest_invoice (related name)",
                "djstripe.Charge.latest_upcominginvoice (related name)",
                "djstripe.Charge.invoice",
                "djstripe.Charge.transfer",
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.PaymentIntent.upcominginvoice (related name)",
            },
        )

        refunded_charge = charge.refund()
        self.assertEqual(refunded_charge.refunded, True)
        self.assertEqual(refunded_charge.amount_refunded, decimal.Decimal("20.00"))

        self.assert_fks(
            refunded_charge,
            expected_blank_fks={
                "djstripe.Account.branding_logo",
                "djstripe.Account.branding_icon",
                "djstripe.Charge.dispute",
                "djstripe.Charge.latest_invoice (related name)",
                "djstripe.Charge.latest_upcominginvoice (related name)",
                "djstripe.Charge.invoice",
                "djstripe.Charge.transfer",
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.PaymentIntent.upcominginvoice (related name)",
            },
        )

    def test_calculate_refund_amount_full_refund(self):
        charge = Charge(
            id="ch_111111", customer=self.customer, amount=decimal.Decimal("500.00")
        )
        self.assertEqual(charge._calculate_refund_amount(), 50000)

    def test_calculate_refund_amount_partial_refund(self):
        charge = Charge(
            id="ch_111111", customer=self.customer, amount=decimal.Decimal("500.00")
        )
        self.assertEqual(
            charge._calculate_refund_amount(amount=decimal.Decimal("300.00")), 30000
        )

    def test_calculate_refund_above_max_refund(self):
        charge = Charge(
            id="ch_111111", customer=self.customer, amount=decimal.Decimal("500.00")
        )
        self.assertEqual(
            charge._calculate_refund_amount(amount=decimal.Decimal("600.00")), 50000
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", autospec=True)
    @patch("stripe.Charge.create", autospec=True)
    @patch("stripe.PaymentIntent.retrieve", autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    def test_charge_converts_dollars_into_cents(
        self,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_create_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": None, "amount": 1000})

        charge_create_mock.return_value = fake_charge_copy
        charge_retrieve_mock.return_value = fake_charge_copy

        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)
        fake_payment_intent.update({"invoice": None})

        payment_intent_retrieve_mock.return_value = fake_payment_intent

        self.customer.charge(amount=decimal.Decimal("10.00"))

        _, kwargs = charge_create_mock.call_args
        self.assertEqual(kwargs["amount"], 1000)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", autospec=True)
    @patch("stripe.Charge.create", autospec=True)
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch("stripe.Invoice.retrieve", autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    def test_charge_doesnt_require_invoice(
        self,
        subscription_retrieve_mock,
        product_retrieve_mock,
        invoice_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_create_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update(
            {"invoice": FAKE_INVOICE["id"], "amount": FAKE_INVOICE["amount_due"]}
        )
        fake_invoice_copy = deepcopy(FAKE_INVOICE)

        charge_create_mock.return_value = fake_charge_copy
        charge_retrieve_mock.return_value = fake_charge_copy
        invoice_retrieve_mock.return_value = fake_invoice_copy

        try:
            self.customer.charge(amount=decimal.Decimal("20.00"))
        except Invoice.DoesNotExist:
            self.fail(msg="Stripe Charge shouldn't throw Invoice DoesNotExist.")

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", autospec=True)
    @patch("stripe.Charge.create", autospec=True)
    @patch("stripe.PaymentIntent.retrieve", autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    def test_charge_passes_extra_arguments(
        self,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_create_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": None})

        charge_create_mock.return_value = fake_charge_copy
        charge_retrieve_mock.return_value = fake_charge_copy

        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)
        fake_payment_intent.update({"invoice": None})

        payment_intent_retrieve_mock.return_value = fake_payment_intent

        self.customer.charge(
            amount=decimal.Decimal("10.00"),
            capture=True,
            destination=FAKE_ACCOUNT["id"],
        )

        _, kwargs = charge_create_mock.call_args
        self.assertEqual(kwargs["capture"], True)
        self.assertEqual(kwargs["destination"], FAKE_ACCOUNT["id"])

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", autospec=True)
    @patch("stripe.Charge.create", autospec=True)
    @patch("stripe.PaymentIntent.retrieve", autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    def test_charge_string_source(
        self,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_create_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": None})

        charge_create_mock.return_value = fake_charge_copy
        charge_retrieve_mock.return_value = fake_charge_copy

        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)
        fake_payment_intent.update({"invoice": None})

        payment_intent_retrieve_mock.return_value = fake_payment_intent

        self.customer.charge(amount=decimal.Decimal("10.00"), source=self.card.id)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", autospec=True)
    @patch("stripe.Charge.create", autospec=True)
    @patch("stripe.PaymentIntent.retrieve", autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    def test_charge_card_source(
        self,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_create_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        fake_charge_copy = deepcopy(FAKE_CHARGE)
        fake_charge_copy.update({"invoice": None})

        charge_create_mock.return_value = fake_charge_copy
        charge_retrieve_mock.return_value = fake_charge_copy

        fake_payment_intent = deepcopy(FAKE_PAYMENT_INTENT_I)
        fake_payment_intent.update({"invoice": None})

        payment_intent_retrieve_mock.return_value = fake_payment_intent

        self.customer.charge(amount=decimal.Decimal("10.00"), source=self.card)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Invoice.list",
        return_value=StripeList(
            data=[deepcopy(FAKE_INVOICE), deepcopy(FAKE_INVOICE_III)]
        ),
        autospec=True,
    )
    @patch("djstripe.models.Invoice.retry", autospec=True)
    def test_retry_unpaid_invoices(
        self,
        invoice_retry_mock,
        invoice_list_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        self.customer.retry_unpaid_invoices()

        invoice = Invoice.objects.get(id=FAKE_INVOICE_III["id"])
        invoice_retry_mock.assert_called_once_with(invoice)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Invoice.list",
        return_value=StripeList(data=[deepcopy(FAKE_INVOICE)]),
        autospec=True,
    )
    @patch("djstripe.models.Invoice.retry", autospec=True)
    def test_retry_unpaid_invoices_none_unpaid(
        self,
        invoice_retry_mock,
        invoice_list_mock,
        product_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        balance_transaction_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account

        self.customer.retry_unpaid_invoices()

        self.assertFalse(invoice_retry_mock.called)

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Invoice.list",
        return_value=StripeList(data=[deepcopy(FAKE_INVOICE_III)]),
    )
    @patch("djstripe.models.Invoice.retry", autospec=True)
    def test_retry_unpaid_invoices_expected_exception(
        self,
        invoice_retry_mock,
        invoice_list_mock,
        product_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account
        invoice_retry_mock.side_effect = InvalidRequestError(
            "Invoice is already paid", "blah"
        )

        try:
            self.customer.retry_unpaid_invoices()
        except Exception:
            self.fail("Exception was unexpectedly raised.")

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Invoice.list",
        return_value=StripeList(data=[deepcopy(FAKE_INVOICE_III)]),
    )
    @patch("djstripe.models.Invoice.retry", autospec=True)
    def test_retry_unpaid_invoices_unexpected_exception(
        self,
        invoice_retry_mock,
        invoice_list_mock,
        product_retrieve_mock,
        charge_retrieve_mock,
        customer_retrieve_mock,
        subscription_retrieve_mock,
        default_account_mock,
    ):
        default_account_mock.return_value = self.account
        invoice_retry_mock.side_effect = InvalidRequestError(
            "This should fail!", "blah"
        )

        with self.assertRaisesMessage(InvalidRequestError, "This should fail!"):
            self.customer.retry_unpaid_invoices()

    @patch("stripe.Invoice.create", autospec=True)
    def test_send_invoice_success(self, invoice_create_mock):
        return_status = self.customer.send_invoice()
        self.assertTrue(return_status)

        invoice_create_mock.assert_called_once_with(
            api_key=STRIPE_SECRET_KEY, customer=self.customer.id
        )

    @patch("stripe.Invoice.create", autospec=True)
    def test_send_invoice_failure(self, invoice_create_mock):
        invoice_create_mock.side_effect = InvalidRequestError(
            "Invoice creation failed.", "blah"
        )

        return_status = self.customer.send_invoice()
        self.assertFalse(return_status)

        invoice_create_mock.assert_called_once_with(
            api_key=STRIPE_SECRET_KEY, customer=self.customer.id
        )

    @patch("stripe.Coupon.retrieve", return_value=deepcopy(FAKE_COUPON), autospec=True)
    def test_sync_customer_with_discount(self, coupon_retrieve_mock):
        self.assertIsNone(self.customer.coupon)
        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["discount"] = deepcopy(FAKE_DISCOUNT_CUSTOMER)
        customer = Customer.sync_from_stripe_data(fake_customer)
        self.assertEqual(customer.coupon.id, FAKE_COUPON["id"])
        self.assertIsNotNone(customer.coupon_start)
        self.assertIsNone(customer.coupon_end)

    @patch("stripe.Coupon.retrieve", return_value=deepcopy(FAKE_COUPON), autospec=True)
    def test_sync_customer_discount_already_present(self, coupon_retrieve_mock):
        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["discount"] = deepcopy(FAKE_DISCOUNT_CUSTOMER)

        # Set the customer's coupon to be what we'll sync
        customer = Customer.objects.get(id=FAKE_CUSTOMER["id"])
        customer.coupon = Coupon.sync_from_stripe_data(FAKE_COUPON)
        customer.save()

        customer = Customer.sync_from_stripe_data(fake_customer)
        self.assertEqual(customer.coupon.id, FAKE_COUPON["id"])

    def test_sync_customer_delete_discount(self):
        test_coupon = Coupon.sync_from_stripe_data(FAKE_COUPON)
        self.customer.coupon = test_coupon
        self.customer.save()
        self.assertEqual(self.customer.coupon.id, FAKE_COUPON["id"])

        customer = Customer.sync_from_stripe_data(FAKE_CUSTOMER)
        self.assertEqual(customer.coupon, None)

    @patch(
        "djstripe.models.Invoice.sync_from_stripe_data",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.Invoice.list",
        return_value=StripeList(
            data=[deepcopy(FAKE_INVOICE), deepcopy(FAKE_INVOICE_III)]
        ),
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_invoices(
        self, customer_retrieve_mock, invoice_list_mock, invoice_sync_mock
    ):
        self.customer._sync_invoices()
        self.assertEqual(2, invoice_sync_mock.call_count)

    @patch(
        "djstripe.models.Invoice.sync_from_stripe_data",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch("stripe.Invoice.list", return_value=StripeList(data=[]), autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_invoices_none(
        self, customer_retrieve_mock, invoice_list_mock, invoice_sync_mock
    ):
        self.customer._sync_invoices()
        self.assertEqual(0, invoice_sync_mock.call_count)

    @patch(
        "djstripe.models.Charge.sync_from_stripe_data",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.Charge.list",
        return_value=StripeList(data=[deepcopy(FAKE_CHARGE)]),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_charges(
        self, customer_retrieve_mock, charge_list_mock, charge_sync_mock
    ):
        self.customer._sync_charges()
        self.assertEqual(1, charge_sync_mock.call_count)

    @patch(
        "djstripe.models.Charge.sync_from_stripe_data",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch("stripe.Charge.list", return_value=StripeList(data=[]), autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_charges_none(
        self, customer_retrieve_mock, charge_list_mock, charge_sync_mock
    ):
        self.customer._sync_charges()
        self.assertEqual(0, charge_sync_mock.call_count)

    @patch(
        "djstripe.models.Subscription.sync_from_stripe_data",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.Subscription.list",
        return_value=StripeList(
            data=[deepcopy(FAKE_SUBSCRIPTION), deepcopy(FAKE_SUBSCRIPTION_II)]
        ),
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_subscriptions(
        self, customer_retrieve_mock, subscription_list_mock, subscription_sync_mock
    ):
        self.customer._sync_subscriptions()
        self.assertEqual(2, subscription_sync_mock.call_count)

    @patch(
        "djstripe.models.Subscription.sync_from_stripe_data",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch("stripe.Subscription.list", return_value=StripeList(data=[]), autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    def test_sync_subscriptions_none(
        self, customer_retrieve_mock, subscription_list_mock, subscription_sync_mock
    ):
        self.customer._sync_subscriptions()
        self.assertEqual(0, subscription_sync_mock.call_count)

    @patch("djstripe.models.Customer.send_invoice", autospec=True)
    @patch(
        "stripe.Subscription.create",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_subscribe_not_charge_immediately(
        self,
        product_retrieve_mock,
        customer_retrieve_mock,
        subscription_create_mock,
        send_invoice_mock,
    ):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        self.customer.subscribe(plan=plan, charge_immediately=False)
        self.assertFalse(send_invoice_mock.called)

    @patch("djstripe.models.Customer.send_invoice", autospec=True)
    @patch(
        "stripe.Subscription.create",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_subscribe_charge_immediately(
        self,
        product_retrieve_mock,
        customer_retrieve_mock,
        subscription_create_mock,
        send_invoice_mock,
    ):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        self.assert_fks(plan, expected_blank_fks={})

        self.customer.subscribe(plan=plan, charge_immediately=True)
        self.assertTrue(send_invoice_mock.called)

    @patch("djstripe.models.Customer.send_invoice", autospec=True)
    @patch(
        "stripe.Subscription.create",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_subscribe_plan_string(
        self,
        product_retrieve_mock,
        customer_retrieve_mock,
        subscription_create_mock,
        send_invoice_mock,
    ):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        self.assert_fks(plan, expected_blank_fks={})

        self.customer.subscribe(plan=plan.id, charge_immediately=True)
        self.assertTrue(send_invoice_mock.called)

    @patch("stripe.Subscription.create", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_subscription_shortcut_with_multiple_subscriptions(
        self, product_retrieve_mock, customer_retrieve_mock, subscription_create_mock
    ):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        self.assert_fks(plan, expected_blank_fks={})

        subscription_fake_duplicate = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake_duplicate["id"] = "sub_6lsC8pt7IcF8jd"

        subscription_create_mock.side_effect = [
            deepcopy(FAKE_SUBSCRIPTION),
            subscription_fake_duplicate,
        ]

        self.customer.subscribe(plan=plan, charge_immediately=False)
        self.customer.subscribe(plan=plan, charge_immediately=False)

        self.assertEqual(2, self.customer.subscriptions.count())
        self.assertEqual(2, len(self.customer.valid_subscriptions))

        with self.assertRaises(MultipleSubscriptionException):
            self.customer.subscription

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_subscription_shortcut_with_invalid_subscriptions(
        self, product_retrieve_mock, customer_retrieve_mock
    ):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        self.assert_fks(plan, expected_blank_fks={})

        fake_subscriptions = [
            deepcopy(FAKE_SUBSCRIPTION),
            deepcopy(FAKE_SUBSCRIPTION),
            deepcopy(FAKE_SUBSCRIPTION),
        ]

        # update the status of all but one to be invalid,
        # we need to also change the id for sync to work
        fake_subscriptions[1]["status"] = "canceled"
        fake_subscriptions[1]["id"] = fake_subscriptions[1]["id"] + "foo1"
        fake_subscriptions[2]["status"] = "incomplete_expired"
        fake_subscriptions[2]["id"] = fake_subscriptions[2]["id"] + "foo2"

        for fake_subscription in fake_subscriptions:
            with patch(
                "stripe.Subscription.create",
                autospec=True,
                side_effect=[fake_subscription],
            ):
                self.customer.subscribe(plan=plan, charge_immediately=False)

        self.assertEqual(3, self.customer.subscriptions.count())
        self.assertEqual(1, len(self.customer.valid_subscriptions))
        self.assertEqual(
            self.customer.valid_subscriptions[0], self.customer.subscription
        )

        self.assertEqual(fake_subscriptions[0]["id"], self.customer.subscription.id)

    @patch("stripe.Subscription.create", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_has_active_subscription_with_unspecified_plan_with_multiple_subscriptions(
        self, product_retrieve_mock, customer_retrieve_mock, subscription_create_mock
    ):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        self.assert_fks(plan, expected_blank_fks={})

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["current_period_end"] = datetime_to_unix(
            timezone.now() + timezone.timedelta(days=7)
        )

        subscription_fake_duplicate = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake_duplicate["current_period_end"] = datetime_to_unix(
            timezone.now() + timezone.timedelta(days=7)
        )
        subscription_fake_duplicate["id"] = "sub_6lsC8pt7IcF8jd"

        subscription_create_mock.side_effect = [
            subscription_fake,
            subscription_fake_duplicate,
        ]

        self.customer.subscribe(plan=plan, charge_immediately=False)
        self.customer.subscribe(plan=plan, charge_immediately=False)

        self.assertEqual(2, self.customer.subscriptions.count())

        with self.assertRaises(TypeError):
            self.customer.has_active_subscription()

    @patch("stripe.Subscription.create", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_has_active_subscription_with_plan(
        self, product_retrieve_mock, customer_retrieve_mock, subscription_create_mock
    ):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["current_period_end"] = datetime_to_unix(
            timezone.now() + timezone.timedelta(days=7)
        )

        subscription_create_mock.return_value = subscription_fake

        self.customer.subscribe(plan=plan, charge_immediately=False)

        self.customer.has_active_subscription(plan=plan)

    @patch("stripe.Subscription.create", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_has_active_subscription_with_plan_string(
        self, product_retrieve_mock, customer_retrieve_mock, subscription_create_mock
    ):
        plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN))

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["current_period_end"] = datetime_to_unix(
            timezone.now() + timezone.timedelta(days=7)
        )

        subscription_create_mock.return_value = subscription_fake

        self.customer.subscribe(plan=plan, charge_immediately=False)

        self.customer.has_active_subscription(plan=plan.id)

    @patch(
        "djstripe.models.InvoiceItem.sync_from_stripe_data",
        return_value="pancakes",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.InvoiceItem.create",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    def test_add_invoice_item(self, invoiceitem_create_mock, invoiceitem_sync_mock):
        invoiceitem = self.customer.add_invoice_item(
            amount=decimal.Decimal("50.00"),
            currency="eur",
            description="test",
            invoice=77,
            subscription=25,
        )
        self.assertEqual("pancakes", invoiceitem)

        invoiceitem_create_mock.assert_called_once_with(
            api_key=STRIPE_SECRET_KEY,
            amount=5000,
            customer=self.customer.id,
            currency="eur",
            description="test",
            discountable=None,
            invoice=77,
            metadata=None,
            subscription=25,
        )

    @patch(
        "djstripe.models.InvoiceItem.sync_from_stripe_data",
        return_value="pancakes",
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    @patch(
        "stripe.InvoiceItem.create",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    def test_add_invoice_item_djstripe_objects(
        self, invoiceitem_create_mock, invoiceitem_sync_mock
    ):
        invoiceitem = self.customer.add_invoice_item(
            amount=decimal.Decimal("50.00"),
            currency="eur",
            description="test",
            invoice=Invoice(id=77),
            subscription=Subscription(id=25),
        )
        self.assertEqual("pancakes", invoiceitem)

        invoiceitem_create_mock.assert_called_once_with(
            api_key=STRIPE_SECRET_KEY,
            amount=5000,
            customer=self.customer.id,
            currency="eur",
            description="test",
            discountable=None,
            invoice=77,
            metadata=None,
            subscription=25,
        )

    def test_add_invoice_item_bad_decimal(self):
        with self.assertRaisesMessage(
            ValueError, "You must supply a decimal value representing dollars."
        ):
            self.customer.add_invoice_item(amount=5000, currency="usd")

    @patch(
        "stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN), autospec=True,
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.upcoming",
        return_value=deepcopy(FAKE_UPCOMING_INVOICE),
        autospec=IS_STATICMETHOD_AUTOSPEC_SUPPORTED,
    )
    def test_upcoming_invoice(
        self,
        invoice_upcoming_mock,
        subscription_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
    ):
        invoice = self.customer.upcoming_invoice()
        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.id)
        self.assertIsNone(invoice.save())

        subscription_retrieve_mock.assert_called_once_with(
            api_key=ANY, expand=ANY, id=FAKE_SUBSCRIPTION["id"], stripe_account=None
        )
        plan_retrieve_mock.assert_not_called()

        items = invoice.invoiceitems.all()
        self.assertEqual(1, len(items))
        self.assertEqual(FAKE_SUBSCRIPTION["id"], items[0].id)

        self.assertIsNotNone(invoice.plan)
        self.assertEqual(FAKE_PLAN["id"], invoice.plan.id)

        invoice._invoiceitems = []
        items = invoice.invoiceitems.all()
        self.assertEqual(0, len(items))
        self.assertIsNotNone(invoice.plan)

    @patch("stripe.Customer.retrieve", autospec=True)
    def test_delete_subscriber_purges_customer(self, customer_retrieve_mock):
        self.user.delete()
        customer = Customer.objects.get(id=FAKE_CUSTOMER["id"])
        self.assertIsNotNone(customer.date_purged)

    @patch("stripe.Customer.retrieve", autospec=True)
    def test_delete_subscriber_without_customer_is_noop(self, customer_retrieve_mock):
        self.user.delete()
        for customer in self.user.djstripe_customers.all():
            self.assertIsNone(customer.date_purged)
