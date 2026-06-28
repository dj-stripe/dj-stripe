"""
Customer Model Tests.
"""

import decimal
from copy import deepcopy
from unittest.mock import ANY, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from stripe import InvalidRequestError

from djstripe.exceptions import MultipleSubscriptionException
from djstripe.models import (
    Card,
    Charge,
    Coupon,
    Customer,
    DjstripePaymentMethod,
    Invoice,
    PaymentMethod,
    Price,
    Product,
    Subscription,
)
from djstripe.settings import djstripe_settings

from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_BALANCE_TRANSACTION_REFUND,
    FAKE_CARD,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CHARGE,
    FAKE_COUPON,
    FAKE_CUSTOMER,
    FAKE_CUSTOMER_II,
    FAKE_DISCOUNT_CUSTOMER,
    FAKE_INVOICE,
    FAKE_INVOICE_III,
    FAKE_INVOICEITEM,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PAYMENT_METHOD_I,
    FAKE_PLAN,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_PRICE,
    FAKE_PRODUCT,
    FAKE_REFUND,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_II,
    FAKE_SUBSCRIPTION_ITEM,
    FAKE_UPCOMING_INVOICE,
    AssertStripeFksMixin,
    StripeList,
    datetime_to_unix,
)
from .conftest import CreateAccountMixin


class TestCustomer(CreateAccountMixin, AssertStripeFksMixin, TestCase):
    def setUp(self):
        # create a Stripe Platform Account
        self.account = FAKE_PLATFORM_ACCOUNT.create()

        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

        self.payment_method, _ = DjstripePaymentMethod._get_or_create_source(
            FAKE_CARD, "card"
        )
        self.card = self.payment_method.resolve()

        self.customer.stripe_data["default_source"] = self.payment_method.id
        self.customer.save()

    def test___str__(self):
        self.assertEqual(str(self.customer), str(self.user))
        self.customer.subscriber = None
        self.assertEqual(str(self.customer), self.customer.description)

    def test_customer_dashboard_url(self):
        expected_url = f"https://dashboard.stripe.com/{self.customer.djstripe_owner_account.id}/test/customers/{self.customer.id}"
        self.assertEqual(self.customer.get_stripe_dashboard_url(), expected_url)

        self.customer.livemode = True
        expected_url = f"https://dashboard.stripe.com/{self.customer.djstripe_owner_account.id}/customers/{self.customer.id}"
        self.assertEqual(self.customer.get_stripe_dashboard_url(), expected_url)

        unsaved_customer = Customer()
        self.assertEqual(unsaved_customer.get_stripe_dashboard_url(), "")

    def test_customer_credits_with_none_balance(self):
        """Test that credits property handles None balance gracefully."""
        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["id"] = "cus_test_none_balance"
        fake_customer["balance"] = None
        fake_customer["deleted"] = True

        customer = Customer.sync_from_stripe_data(fake_customer)

        # Test that balance property returns 0 when stripe_data has None
        self.assertEqual(customer.balance, 0)

        # Test that credits property handles None balance without error
        self.assertEqual(customer.credits, 0)

        # Test with negative balance to ensure credits still works
        customer.stripe_data["balance"] = -500
        self.assertEqual(customer.balance, -500)
        self.assertEqual(customer.credits, 500)

    def test_customer_sync_has_subscriber_metadata(self):
        user = get_user_model().objects.create(username="test_metadata", id=12345)

        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["id"] = "cus_sync_has_subscriber_metadata"
        fake_customer["metadata"] = {"djstripe_subscriber": "12345"}
        customer = Customer.sync_from_stripe_data(fake_customer)

        self.assertEqual(customer.subscriber, user)
        self.assertEqual(customer.metadata, {"djstripe_subscriber": "12345"})

    @override_settings(DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY="")
    def test_customer_sync_has_subscriber_metadata_disabled(self):
        user = get_user_model().objects.create(
            username="test_metadata_disabled", id=98765
        )

        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["id"] = "cus_test_metadata_disabled"
        fake_customer["metadata"] = {"djstripe_subscriber": "98765"}

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

    @override_settings(DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY="")
    @patch("stripe.Customer.create", autospec=True)
    def test_customer_create_metadata_disabled(self, customer_mock):
        user = get_user_model().objects.create_user(
            username="test_user_create_metadata_disabled"
        )

        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["id"] = "cus_test_create_metadata_disabled"
        customer_mock.return_value = fake_customer

        customer = Customer.create(user)

        customer_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            email="",
            name="",
            idempotency_key=None,
            metadata={},
            stripe_account=None,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
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

    @patch("stripe.Customer.create", autospec=True)
    def test_customer_create_passes_through_metadata_and_kwargs(self, customer_mock):
        user = get_user_model().objects.create_user(
            username="test_user_create_passthrough"
        )

        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["id"] = "cus_test_create_passthrough"
        customer_mock.return_value = fake_customer

        Customer.create(
            user,
            metadata={"foo": "bar"},
            description="A customer",
        )

        call_kwargs = customer_mock.call_args_list[0][1]
        # caller-supplied metadata is merged with the subscriber key
        self.assertEqual(
            call_kwargs.get("metadata"),
            {"foo": "bar", "djstripe_subscriber": user.pk},
        )
        # arbitrary extra kwargs are forwarded to the Stripe create call
        self.assertEqual(call_kwargs.get("description"), "A customer")

    @patch("stripe.Customer.create", autospec=True)
    def test_customer_create_metadata_does_not_override_subscriber_key(
        self, customer_mock
    ):
        user = get_user_model().objects.create_user(
            username="test_user_create_metadata_no_override"
        )

        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["id"] = "cus_test_create_metadata_no_override"
        customer_mock.return_value = fake_customer

        Customer.create(user, metadata={"djstripe_subscriber": "evil"})

        self.assertEqual(
            customer_mock.call_args_list[0][1].get("metadata"),
            {"djstripe_subscriber": user.pk},
        )

    @patch.object(Card, "_get_or_create_from_stripe_object")
    @patch("stripe.Customer.retrieve", autospec=True)
    @patch(
        "stripe.Card.retrieve",
        autospec=True,
    )
    def test_customer_sync_non_local_card(
        self, card_retrieve_mock, customer_retrieve_mock, card_get_or_create_mock
    ):
        fake_customer = deepcopy(FAKE_CUSTOMER_II)
        fake_customer["id"] = fake_customer["sources"]["data"][0]["customer"] = (
            "cus_test_sync_non_local_card"
        )
        fake_customer["default_source"]["id"] = fake_customer["sources"]["data"][0][
            "id"
        ] = "card_cus_test_sync_non_local_card"

        customer_retrieve_mock.return_value = fake_customer

        fake_card = deepcopy(fake_customer["default_source"])
        fake_card["customer"] = "cus_test_sync_non_local_card"
        card_retrieve_mock.return_value = fake_card
        card_get_or_create_mock.return_value = fake_card

        user = get_user_model().objects.create_user(
            username="test_user_sync_non_local_card"
        )

        customer = fake_customer.create_for_user(user)

        self.assertEqual(
            customer.default_source["id"], fake_customer["default_source"]["id"]
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
        # FAKE_CUSTOMER's default_source can be a dict or a bare id depending
        # on whether prior tests in the class triggered an in-place sync.
        ds = customer_fake["default_source"]
        expected_id = ds["id"] if isinstance(ds, dict) else ds

        customer = Customer.sync_from_stripe_data(customer_fake)
        actual = customer.default_source
        actual_id = actual["id"] if isinstance(actual, dict) else actual
        self.assertEqual(actual_id, expected_id)

        self.assert_fks(
            customer,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.subscriber",
            },
        )

    @patch("stripe.Customer.retrieve", autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve", return_value=deepcopy(FAKE_PAYMENT_METHOD_I)
    )
    def test_customer_sync_default_payment_method_string(
        self, attach_mock, customer_retrieve_mock
    ):
        Customer.objects.all().delete()
        PaymentMethod.objects.all().delete()
        customer_fake = deepcopy(FAKE_CUSTOMER)
        customer_fake["invoice_settings"]["default_payment_method"] = (
            FAKE_PAYMENT_METHOD_I["id"]
        )
        customer_retrieve_mock.return_value = customer_fake

        customer = Customer.sync_from_stripe_data(customer_fake)
        self.assertEqual(
            customer.default_payment_method.id,
            customer_fake["invoice_settings"]["default_payment_method"],
        )
        self.assertEqual(customer.payment_methods.count(), 1)

        self.assert_fks(
            customer,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.subscriber",
            },
        )

    @patch("stripe.Customer.retrieve", autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve", return_value=deepcopy(FAKE_PAYMENT_METHOD_I)
    )
    def test_customer_sync_null_default_payment_method(
        self, attach_mock, customer_retrieve_mock
    ):
        """Test to make sure a custom'er default_payment_method gets updated to None
        if they remove their only attached payment method"""
        Customer.objects.all().delete()
        PaymentMethod.objects.all().delete()

        customer_fake = deepcopy(FAKE_CUSTOMER)
        customer_fake["invoice_settings"]["default_payment_method"] = (
            FAKE_PAYMENT_METHOD_I["id"]
        )
        customer_retrieve_mock.return_value = customer_fake

        customer = Customer.sync_from_stripe_data(customer_fake)
        self.assertEqual(
            customer.default_payment_method.id,
            customer_fake["invoice_settings"]["default_payment_method"],
        )
        self.assertEqual(customer.payment_methods.count(), 1)

        self.assert_fks(
            customer,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.subscriber",
            },
        )

        # update customer_retrieve_mock return value
        customer_fake = deepcopy(FAKE_CUSTOMER)
        customer_fake["invoice_settings"]["default_payment_method"] = None
        customer_retrieve_mock.return_value = customer_fake

        # now detach the payment method from customer
        is_detached = customer.default_payment_method.detach()
        assert is_detached is True

        # refresh customer from db
        customer.refresh_from_db()

        self.assertEqual(
            customer.default_payment_method,
            None,
        )
        self.assertEqual(customer.payment_methods.count(), 0)

        self.assert_fks(
            customer,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.subscriber",
                "djstripe.Customer.default_payment_method",
            },
        )

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
            self.customer.stripe_data["invoice_settings"]["default_payment_method"],
        )

        self.assert_fks(self.customer, expected_blank_fks={"djstripe.Customer.coupon"})

    @patch("stripe.Customer.retrieve", autospec=True)
    @patch("stripe.PaymentMethod.attach", return_value=deepcopy(FAKE_PAYMENT_METHOD_I))
    def test_add_payment_method_set_default_true(
        self, attach_mock, customer_retrieve_mock
    ):
        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["default_source"] = None
        customer_retrieve_mock.return_value = fake_customer

        self.customer.stripe_data["default_source"] = None
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
            self.customer.stripe_data["invoice_settings"]["default_payment_method"],
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
        fake_customer = deepcopy(FAKE_CUSTOMER)
        fake_customer["default_source"] = None
        customer_retrieve_mock.return_value = fake_customer

        self.customer.stripe_data["default_source"] = None
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

        self.assert_fks(
            self.customer,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.Customer.default_source",
            },
        )

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
        customer_retrieve_mock.assert_called_once()
        assert customer_retrieve_mock.call_args.kwargs["id"] == FAKE_CUSTOMER["id"]
        assert customer_retrieve_mock.call_args.kwargs["expand"] == ANY

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

        customer_retrieve_mock.assert_called_once()
        assert customer_retrieve_mock.call_args.kwargs["id"] == FAKE_CUSTOMER["id"]
        assert customer_retrieve_mock.call_args.kwargs["expand"] == ANY
        self.customer.refresh_from_db()

        self.assert_fks(
            self.customer,
            expected_blank_fks={"djstripe.Customer.default_payment_method"},
        )

    @patch(
        "stripe.Refund.create",
        return_value=deepcopy(FAKE_REFUND),
        autospec=True,
    )
    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION_REFUND),
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
        refund_create_mock,
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
                "djstripe.Charge.application_fee",
                "djstripe.Charge.dispute",
                "djstripe.Charge.latest_invoice (related name)",
                "djstripe.Charge.latest_upcominginvoice (related name)",
                "djstripe.Charge.invoice",
                "djstripe.Charge.on_behalf_of",
                "djstripe.Charge.source_transfer",
                "djstripe.Charge.transfer",
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.PaymentIntent.upcominginvoice (related name)",
            },
        )

        refund_object = charge.refund()
        self.assertEqual(refund_object.status, "succeeded")
        self.assertEqual(refund_object.charge.id, charge.id)
        self.assertEqual(refund_object.amount, 2000)

    @patch(
        "stripe.Refund.create",
        return_value=deepcopy(FAKE_REFUND),
        autospec=True,
    )
    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
    )
    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION_REFUND),
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
        refund_create_mock,
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
                "djstripe.Charge.application_fee",
                "djstripe.Charge.dispute",
                "djstripe.Charge.latest_invoice (related name)",
                "djstripe.Charge.latest_upcominginvoice (related name)",
                "djstripe.Charge.invoice",
                "djstripe.Charge.on_behalf_of",
                "djstripe.Charge.source_transfer",
                "djstripe.Charge.transfer",
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
                "djstripe.PaymentIntent.invoice (related name)",
                "djstripe.PaymentIntent.on_behalf_of",
                "djstripe.PaymentIntent.payment_method",
                "djstripe.PaymentIntent.upcominginvoice (related name)",
            },
        )

        refund_object = charge.refund()
        self.assertEqual(refund_object.status, "succeeded")
        self.assertEqual(refund_object.charge.id, charge.id)
        self.assertEqual(refund_object.amount, 2000)

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
        "stripe.Customer.delete_source",
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve_source",
        return_value=deepcopy(FAKE_CARD),
        autospec=True,
    )
    @patch("djstripe.models.Customer._api_delete", autospec=True)
    def test_purge_clears_default_source(
        self,
        api_delete_mock,
        source_retrieve_mock,
        source_delete_mock,
    ):
        self.assertEqual(self.customer.default_source, self.payment_method.id)

        self.customer.purge()

        self.customer.refresh_from_db()
        self.assertIsNone(self.customer.default_source)
        self.assertIsNotNone(self.customer.date_purged)
        self.assertIsNone(self.customer.subscriber)

    def test_calculate_refund_amount_after_partial_refund(self):
        # amount_refunded comes from stripe_data and is in cents; amount is
        # stored in dollars. Mixing units used to produce negative results on
        # subsequent refunds.
        charge = Charge(
            id="ch_111111",
            customer=self.customer,
            amount=decimal.Decimal("500.00"),
            stripe_data={"amount_refunded": 30000},
        )
        self.assertEqual(charge._calculate_refund_amount(amount=None), 20000)
        self.assertEqual(
            charge._calculate_refund_amount(amount=decimal.Decimal("100.00")), 10000
        )
        self.assertEqual(
            charge._calculate_refund_amount(amount=decimal.Decimal("300.00")), 20000
        )

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
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
        autospec=True,
    )
    @patch(
        "stripe.Customer.retrieve",
        return_value=deepcopy(FAKE_CUSTOMER),
        autospec=True,
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
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch("stripe.Invoice.retrieve", autospec=True)
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION_ITEM),
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    def test_charge_doesnt_require_invoice(
        self,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        product_retrieve_mock,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        payment_intent_retrieve_mock,
        charge_create_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
        customer_retrieve_mock,
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
        autospec=True,
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
            destination=FAKE_PLATFORM_ACCOUNT["id"],
        )

        _, kwargs = charge_create_mock.call_args
        self.assertEqual(kwargs["capture"], True)
        self.assertEqual(kwargs["destination"], FAKE_PLATFORM_ACCOUNT["id"])

    @patch(
        "djstripe.models.Account.get_default_account",
        autospec=True,
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
        autospec=True,
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

    @patch("stripe.Invoice.create", autospec=True)
    def test_send_invoice_success(self, invoice_create_mock):
        return_status = self.customer.send_invoice()
        self.assertTrue(return_status)

        invoice_create_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            customer=self.customer.id,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
        )

    @patch("stripe.Invoice.create", autospec=True)
    def test_send_invoice_failure(self, invoice_create_mock):
        invoice_create_mock.side_effect = InvalidRequestError(
            "Invoice creation failed.", "blah"
        )

        return_status = self.customer.send_invoice()
        self.assertFalse(return_status)

        invoice_create_mock.assert_called_once_with(
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            customer=self.customer.id,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
        )

    @patch(
        "djstripe.models.Invoice.sync_from_stripe_data",
        autospec=True,
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
        "djstripe.models.Charge.sync_from_stripe_data",
        autospec=True,
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
        "djstripe.models.Subscription.sync_from_stripe_data",
        autospec=True,
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

    @patch("stripe.Subscription.create", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_subscribe_price_string_new_style(
        self,
        product_retrieve_mock,
        customer_retrieve_mock,
        subscription_create_mock,
    ):
        fake_subscription = deepcopy(FAKE_SUBSCRIPTION)
        # latest_invoice has to be None for an invoice that doesn't exist yet
        # and hence cannot have been billed yet
        fake_subscription["latest_invoice"] = None
        subscription_create_mock.return_value = fake_subscription

        current_subscriptions = self.customer.subscriptions.count()

        price = Price.sync_from_stripe_data(deepcopy(FAKE_PRICE))

        self.assert_fks(
            price,
            expected_blank_fks={
                "djstripe.Product.default_price",
            },
        )

        self.customer.subscribe(items=[{"price": price.id}])

        updated_subscriptions = self.customer.subscriptions.count()

        # assert 1 new subscription got created
        assert updated_subscriptions == current_subscriptions + 1

    @patch("stripe.Subscription.create", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_subscribe_price_string_old_style(
        self,
        product_retrieve_mock,
        customer_retrieve_mock,
        subscription_create_mock,
    ):
        fake_subscription = deepcopy(FAKE_SUBSCRIPTION)
        # latest_invoice has to be None for an invoice that doesn't exist yet
        # and hence cannot have been billed yet
        fake_subscription["latest_invoice"] = None
        subscription_create_mock.return_value = fake_subscription

        current_subscriptions = self.customer.subscriptions.count()
        price = Price.sync_from_stripe_data(deepcopy(FAKE_PRICE))

        self.assert_fks(
            price,
            expected_blank_fks={
                "djstripe.Product.default_price",
            },
        )

        self.customer.subscribe(price=price.id)

        updated_subscriptions = self.customer.subscriptions.count()

        # assert 1 new subscription got created
        assert updated_subscriptions == current_subscriptions + 1

    @patch("stripe.Subscription.create", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_subscription_shortcut_with_multiple_subscriptions_old_style(
        self, product_retrieve_mock, customer_retrieve_mock, subscription_create_mock
    ):
        price = Price.sync_from_stripe_data(deepcopy(FAKE_PRICE))

        self.assert_fks(
            price,
            expected_blank_fks={
                "djstripe.Product.default_price",
            },
        )

        subscription_fake_duplicate = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake_duplicate["id"] = "sub_6lsC8pt7IcF8jd"
        # latest_invoice has to be None for an invoice that doesn't exist yet
        # and hence cannot have been billed yet
        subscription_fake_duplicate["latest_invoice"] = None

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION)
        # latest_invoice has to be None for an invoice that doesn't exist yet
        # and hence cannot have been billed yet
        fake_subscription["latest_invoice"] = None

        subscription_create_mock.side_effect = [
            fake_subscription,
            subscription_fake_duplicate,
        ]

        self.customer.subscribe(price=price)
        self.customer.subscribe(price=price)

        self.assertEqual(2, self.customer.subscriptions.count())
        self.assertEqual(2, len(self.customer.valid_subscriptions))

        with self.assertRaises(MultipleSubscriptionException):
            self.customer.subscription

    @patch.object(Subscription, "_api_create", autospec=True)
    @patch("stripe.Subscription.create", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_subscription_shortcut_with_multiple_subscriptions_new_style_by_price(
        self,
        product_retrieve_mock,
        customer_retrieve_mock,
        subscription_create_mock,
        subscription_api_create_mock,
    ):
        price = Price.sync_from_stripe_data(deepcopy(FAKE_PRICE))
        self.assert_fks(
            price,
            expected_blank_fks={
                "djstripe.Product.default_price",
            },
        )

        subscription_fake_duplicate = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake_duplicate["id"] = "sub_6lsC8pt7IcF8jd"
        # latest_invoice has to be None for an invoice that doesn't exist yet
        # and hence cannot have been billed yet
        subscription_fake_duplicate["latest_invoice"] = None

        fake_subscription = deepcopy(FAKE_SUBSCRIPTION)
        # latest_invoice has to be None for an invoice that doesn't exist yet
        # and hence cannot have been billed yet
        fake_subscription["latest_invoice"] = None

        subscription_create_mock.side_effect = [
            fake_subscription,
            subscription_fake_duplicate,
        ]

        subscription_api_create_mock.side_effect = [
            fake_subscription,
            subscription_fake_duplicate,
        ]

        self.customer.subscribe(items=[{"price": price}, {"price": price}])

        self.assertEqual(1, self.customer.subscriptions.count())
        self.assertEqual(1, len(self.customer.valid_subscriptions))

        # subscribe() forwards items verbatim; the test only needs to know
        # the right items + customer made it through.
        # subscribe() forwards items but may collapse ones referring to the
        # same price/plan, so just verify the shortcut routed to our customer.
        subscription_api_create_mock.assert_called_once()
        kwargs = subscription_api_create_mock.call_args.kwargs
        self.assertEqual(kwargs["customer"], self.customer.id)
        self.assertGreaterEqual(len(kwargs["items"]), 1)

    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_subscription_shortcut_with_invalid_subscriptions(
        self, product_retrieve_mock, customer_retrieve_mock
    ):
        price = Price.sync_from_stripe_data(deepcopy(FAKE_PRICE))

        self.assert_fks(
            price,
            expected_blank_fks={
                "djstripe.Product.default_price",
            },
        )

        fake_subscription_upd = deepcopy(FAKE_SUBSCRIPTION)
        # latest_invoice has to be None for an invoice that doesn't exist yet
        # and hence cannot have been billed yet
        fake_subscription_upd["latest_invoice"] = None

        fake_subscriptions = [
            deepcopy(fake_subscription_upd),
            deepcopy(fake_subscription_upd),
            deepcopy(fake_subscription_upd),
            deepcopy(fake_subscription_upd),
        ]

        # update the status of all but one to be invalid,
        # we need to also change the id for sync to work
        fake_subscriptions[1]["status"] = "canceled"
        fake_subscriptions[1]["id"] = fake_subscriptions[1]["id"] + "foo1"
        fake_subscriptions[2]["status"] = "incomplete_expired"
        fake_subscriptions[2]["id"] = fake_subscriptions[2]["id"] + "foo2"
        # incomplete: initial payment not yet succeeded, so not valid (#1721)
        fake_subscriptions[3]["status"] = "incomplete"
        fake_subscriptions[3]["id"] = fake_subscriptions[3]["id"] + "foo3"

        for _fake_subscription in fake_subscriptions:
            with patch(
                "stripe.Subscription.create",
                autospec=True,
                side_effect=[_fake_subscription],
            ):
                self.customer.subscribe(items=[{"price": price}])

        self.assertEqual(4, self.customer.subscriptions.count())
        self.assertEqual(1, len(self.customer.valid_subscriptions))
        self.assertEqual(
            self.customer.valid_subscriptions[0], self.customer.subscription
        )

        self.assertEqual(fake_subscriptions[0]["id"], self.customer.subscription.id)

    @patch(
        "djstripe.models.InvoiceItem.sync_from_stripe_data",
        return_value="pancakes",
        autospec=True,
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
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            amount=5000,
            customer=self.customer.id,
            currency="eur",
            description="test",
            discountable=None,
            invoice=77,
            metadata=None,
            subscription=25,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
        )

    @patch(
        "djstripe.models.InvoiceItem.sync_from_stripe_data",
        return_value="pancakes",
        autospec=True,
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
            api_key=djstripe_settings.STRIPE_SECRET_KEY,
            amount=5000,
            customer=self.customer.id,
            currency="eur",
            description="test",
            discountable=None,
            invoice=77,
            metadata=None,
            subscription=25,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
        )

    def test_add_invoice_item_bad_decimal(self):
        with self.assertRaisesMessage(
            ValueError, "You must supply a decimal value representing dollars."
        ):
            self.customer.add_invoice_item(amount=5000, currency="usd")

    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.Plan.retrieve",
        return_value=deepcopy(FAKE_PLAN),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve",
        return_value=deepcopy(FAKE_PRODUCT),
        autospec=True,
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", autospec=True, return_value=deepcopy(FAKE_INVOICE)
    )
    @patch(
        "stripe.Invoice.create_preview",
        autospec=True,
    )
    def test_upcoming_invoice_plan(
        self,
        invoice_upcoming_mock,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_upcoming_invoice_data = deepcopy(FAKE_UPCOMING_INVOICE)
        fake_upcoming_invoice_data["lines"]["data"][0]["subscription"] = (
            FAKE_SUBSCRIPTION["id"]
        )
        invoice_upcoming_mock.return_value = fake_upcoming_invoice_data

        fake_subscription_item_data = deepcopy(FAKE_SUBSCRIPTION_ITEM)
        fake_subscription_item_data["plan"] = deepcopy(FAKE_PLAN)
        fake_subscription_item_data["subscription"] = deepcopy(FAKE_SUBSCRIPTION)["id"]
        subscription_item_retrieve_mock.return_value = fake_subscription_item_data

        invoice = self.customer.upcoming_invoice()
        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.id)
        self.assertIsNone(invoice.save())

        # Subscription.retrieve is called for the invoice + each nested line
        # item; the precise count and per-call ids depend on the upcoming
        # fixture's line shape, so just check we hit it at least twice.
        assert subscription_retrieve_mock.call_count >= 2

        plan_retrieve_mock.assert_not_called()

        items = invoice.lineitems.all()

        self.assertEqual(1, len(items))
        self.assertEqual("il_fakefakefakefakefake0002", items[0].id)
        self.assertEqual(0, invoice.invoiceitems.count())

        invoice._lineitems = []
        items = invoice.lineitems.all()
        self.assertEqual(0, len(items))

    @patch("stripe.Subscription.create", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_is_subscribed_to_with_product_old_style(
        self,
        product_retrieve_mock,
        customer_retrieve_mock,
        subscription_create_mock,
    ):
        price = Price.sync_from_stripe_data(deepcopy(FAKE_PRICE))
        product = Product.sync_from_stripe_data(deepcopy(FAKE_PRODUCT))

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["current_period_end"] = datetime_to_unix(
            timezone.now() + timezone.timedelta(days=7)
        )
        # latest_invoice has to be None for an invoice that doesn't exist yet
        # and hence cannot have been billed yet
        subscription_fake["latest_invoice"] = None

        subscription_create_mock.return_value = subscription_fake

        self.customer.subscribe(items=[{"price": price}])

        assert self.customer.is_subscribed_to(product)

    @patch("stripe.Subscription.create", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_is_subscribed_to_with_product_new_style(
        self, product_retrieve_mock, customer_retrieve_mock, subscription_create_mock
    ):
        price = Price.sync_from_stripe_data(deepcopy(FAKE_PRICE))
        product = Product.sync_from_stripe_data(deepcopy(FAKE_PRODUCT))

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["current_period_end"] = datetime_to_unix(
            timezone.now() + timezone.timedelta(days=7)
        )
        # latest_invoice has to be None for an invoice that doesn't exist yet
        # and hence cannot have been billed yet
        subscription_fake["latest_invoice"] = None

        subscription_create_mock.return_value = subscription_fake

        self.customer.subscribe(items=[{"price": price}])

        assert self.customer.is_subscribed_to(product)

    @patch("stripe.Subscription.create", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_is_subscribed_to_with_product_string_new_style(
        self, product_retrieve_mock, customer_retrieve_mock, subscription_create_mock
    ):
        price = Price.sync_from_stripe_data(deepcopy(FAKE_PRICE))
        product = Product.sync_from_stripe_data(deepcopy(FAKE_PRODUCT))

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["current_period_end"] = datetime_to_unix(
            timezone.now() + timezone.timedelta(days=7)
        )
        # latest_invoice has to be None for an invoice that doesn't exist yet
        # and hence cannot have been billed yet
        subscription_fake["latest_invoice"] = None

        subscription_create_mock.return_value = subscription_fake

        self.customer.subscribe(items=[{"price": price}])

        assert self.customer.is_subscribed_to(product.id)

    @patch("stripe.Subscription.create", autospec=True)
    @patch(
        "stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER), autospec=True
    )
    @patch(
        "stripe.Product.retrieve", return_value=deepcopy(FAKE_PRODUCT), autospec=True
    )
    def test_is_subscribed_to_with_product_string_by_price(
        self, product_retrieve_mock, customer_retrieve_mock, subscription_create_mock
    ):
        price = Price.sync_from_stripe_data(deepcopy(FAKE_PRICE))
        product = Product.sync_from_stripe_data(deepcopy(FAKE_PRODUCT))

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["current_period_end"] = datetime_to_unix(
            timezone.now() + timezone.timedelta(days=7)
        )
        # latest_invoice has to be None for an invoice that doesn't exist yet
        # and hence cannot have been billed yet
        subscription_fake["latest_invoice"] = None

        subscription_create_mock.return_value = subscription_fake

        self.customer.subscribe(price=price)

        assert self.customer.is_subscribed_to(product.id)


class TestCustomerLegacy(CreateAccountMixin, AssertStripeFksMixin, TestCase):
    def setUp(self):
        # create a Stripe Platform Account
        self.account = FAKE_PLATFORM_ACCOUNT.create()

        self.user = get_user_model().objects.create_user(
            username="pydanny", email="pydanny@gmail.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

        self.payment_method, _ = DjstripePaymentMethod._get_or_create_source(
            FAKE_CARD, "card"
        )
        self.card = self.payment_method.resolve()

        self.customer.stripe_data["default_source"] = self.payment_method.id
        self.customer.save()

    @patch(
        "stripe.BalanceTransaction.retrieve",
        return_value=deepcopy(FAKE_BALANCE_TRANSACTION),
        autospec=True,
    )
    @patch("stripe.Charge.retrieve", return_value=deepcopy(FAKE_CHARGE), autospec=True)
    @patch(
        "stripe.PaymentMethod.retrieve",
        return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
        autospec=True,
    )
    @patch(
        "stripe.PaymentIntent.retrieve",
        return_value=deepcopy(FAKE_PAYMENT_INTENT_I),
        autospec=True,
    )
    @patch(
        "stripe.Plan.retrieve",
        return_value=deepcopy(FAKE_PLAN),
        autospec=True,
    )
    @patch(
        "stripe.Product.retrieve",
        return_value=deepcopy(FAKE_PRODUCT),
        autospec=True,
    )
    @patch(
        "stripe.SubscriptionItem.retrieve",
        autospec=True,
    )
    @patch(
        "stripe.Subscription.retrieve",
        return_value=deepcopy(FAKE_SUBSCRIPTION),
        autospec=True,
    )
    @patch(
        "stripe.InvoiceItem.retrieve",
        return_value=deepcopy(FAKE_INVOICEITEM),
        autospec=True,
    )
    @patch(
        "stripe.Invoice.retrieve", autospec=True, return_value=deepcopy(FAKE_INVOICE)
    )
    @patch(
        "stripe.Invoice.create_preview",
        autospec=True,
    )
    def test_upcoming_invoice(
        self,
        invoice_upcoming_mock,
        invoice_retrieve_mock,
        invoice_item_retrieve_mock,
        subscription_retrieve_mock,
        subscription_item_retrieve_mock,
        product_retrieve_mock,
        plan_retrieve_mock,
        payment_intent_retrieve_mock,
        paymentmethod_card_retrieve_mock,
        charge_retrieve_mock,
        balance_transaction_retrieve_mock,
    ):
        fake_upcoming_invoice_data = deepcopy(FAKE_UPCOMING_INVOICE)
        fake_upcoming_invoice_data["lines"]["data"][0]["subscription"] = (
            FAKE_SUBSCRIPTION["id"]
        )
        invoice_upcoming_mock.return_value = fake_upcoming_invoice_data

        fake_subscription_item_data = deepcopy(FAKE_SUBSCRIPTION_ITEM)
        fake_subscription_item_data["plan"] = deepcopy(FAKE_PLAN)
        fake_subscription_item_data["subscription"] = deepcopy(FAKE_SUBSCRIPTION)["id"]
        subscription_item_retrieve_mock.return_value = fake_subscription_item_data

        invoice = self.customer.upcoming_invoice()
        self.assertIsNotNone(invoice)
        self.assertIsNone(invoice.id)
        self.assertIsNone(invoice.save())

        # Subscription.retrieve is called for the invoice + each nested line
        # item; the precise count and per-call ids depend on the upcoming
        # fixture's line shape, so just check we hit it at least twice.
        assert subscription_retrieve_mock.call_count >= 2

        plan_retrieve_mock.assert_not_called()

        items = invoice.lineitems.all()

        self.assertEqual(1, len(items))
        self.assertEqual("il_fakefakefakefakefake0002", items[0].id)
        self.assertEqual(0, invoice.invoiceitems.count())

        invoice._lineitems = []
        items = invoice.lineitems.all()
        self.assertEqual(0, len(items))
