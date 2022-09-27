"""
dj-stripe PaymenthMethod Model Tests.
"""
import sys
from copy import deepcopy
from unittest.mock import patch

import pytest
import stripe
from django.contrib.auth import get_user_model
from django.test import TestCase
from stripe.error import InvalidRequestError

from djstripe import enums, models

from . import (
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CUSTOMER,
    FAKE_PAYMENT_METHOD_I,
    AssertStripeFksMixin,
    PaymentMethodDict,
)

pytestmark = pytest.mark.django_db


class TestPaymentMethod:

    #
    # Helper Methods for monkeypatching
    #

    def mock_customer_get(*args, **kwargs):
        return deepcopy(FAKE_CUSTOMER)

    @pytest.mark.parametrize("customer_exists", [True, False])
    def test___str__(self, monkeypatch, customer_exists):

        # monkeypatch stripe.Customer.retrieve call to return
        # the desired json response.
        monkeypatch.setattr(stripe.Customer, "retrieve", self.mock_customer_get)

        fake_payment_method_data = deepcopy(FAKE_PAYMENT_METHOD_I)
        if not customer_exists:
            fake_payment_method_data["customer"] = None
            pm = models.PaymentMethod.sync_from_stripe_data(fake_payment_method_data)
            customer = None
            assert (
                f"{enums.PaymentMethodType.humanize(fake_payment_method_data['type'])} is not associated with any customer"
            ) == str(pm)

        else:
            pm = models.PaymentMethod.sync_from_stripe_data(fake_payment_method_data)
            customer = models.Customer.objects.get(
                id=fake_payment_method_data["customer"]
            )
            assert (
                f"{enums.PaymentMethodType.humanize(fake_payment_method_data['type'])} for {customer}"
            ) == str(pm)

    @pytest.mark.parametrize("customer_exists", [True, False])
    def test_get_stripe_dashboard_url(self, monkeypatch, customer_exists):

        # monkeypatch stripe.Customer.retrieve call to return
        # the desired json response.
        monkeypatch.setattr(stripe.Customer, "retrieve", self.mock_customer_get)

        fake_payment_method_data = deepcopy(FAKE_PAYMENT_METHOD_I)
        if not customer_exists:
            fake_payment_method_data["customer"] = None
            pm = models.PaymentMethod.sync_from_stripe_data(fake_payment_method_data)
            assert pm
            assert pm.get_stripe_dashboard_url() == ""

        else:
            pm = models.PaymentMethod.sync_from_stripe_data(fake_payment_method_data)
            assert pm
            customer = models.Customer.objects.get(
                id=fake_payment_method_data["customer"]
            )
            assert pm.get_stripe_dashboard_url() == customer.get_stripe_dashboard_url()

    @pytest.mark.parametrize("customer_exists", [True, False])
    def test_sync_from_stripe_data(self, monkeypatch, customer_exists):

        # monkeypatch stripe.Customer.retrieve call to return
        # the desired json response.
        monkeypatch.setattr(stripe.Customer, "retrieve", self.mock_customer_get)

        fake_payment_method_data = deepcopy(FAKE_PAYMENT_METHOD_I)
        if not customer_exists:
            fake_payment_method_data["customer"] = None

        pm = models.PaymentMethod.sync_from_stripe_data(fake_payment_method_data)
        assert pm
        assert pm.id == fake_payment_method_data["id"]


class PaymentMethodTest(AssertStripeFksMixin, TestCase):
    def setUp(self):

        user = get_user_model().objects.create_user(
            username="testuser", email="djstripe@example.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(user)

    # stripe modifies attach() at compile time, which is why
    # another stripe classmethod is decorated.
    # See Here:
    # https://github.com/stripe/stripe-python/blob/master/stripe/api_resources/payment_method.py#L10
    # https://github.com/stripe/stripe-python/blob/master/stripe/api_resources/abstract/custom_method.py#L35
    @patch(
        "stripe.PaymentMethod._cls_attach",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
        autospec=True,
    )
    def test_attach(self, attach_mock):

        payment_method = models.PaymentMethod.attach(
            FAKE_PAYMENT_METHOD_I["id"], customer=FAKE_CUSTOMER["id"]
        )

        self.assert_fks(
            payment_method,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
            },
        )

    @patch(
        "stripe.PaymentMethod._cls_attach",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
        autospec=True,
    )
    def test_attach_obj(self, attach_mock):
        pm = models.PaymentMethod.sync_from_stripe_data(FAKE_PAYMENT_METHOD_I)
        assert pm

        payment_method = models.PaymentMethod.attach(pm, customer=self.customer)

        self.assert_fks(
            payment_method,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
            },
        )

    @patch(
        "stripe.PaymentMethod._cls_attach",
        return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
        autospec=True,
    )
    def test_attach_synced(self, attach_mock):
        fake_payment_method = deepcopy(FAKE_PAYMENT_METHOD_I)
        fake_payment_method["customer"] = None

        payment_method = models.PaymentMethod.sync_from_stripe_data(fake_payment_method)
        assert payment_method

        self.assert_fks(
            payment_method, expected_blank_fks={"djstripe.PaymentMethod.customer"}
        )

        payment_method = models.PaymentMethod.attach(
            payment_method.id, customer=FAKE_CUSTOMER["id"]
        )

        self.assert_fks(
            payment_method,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
            },
        )

    def test_detach(self):
        original_detach = PaymentMethodDict.detach

        def mocked_detach(*args, **kwargs):
            return original_detach(*args, **kwargs)

        with patch(
            "stripe.PaymentMethod.retrieve",
            return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
            autospec=True,
        ):
            models.PaymentMethod.sync_from_stripe_data(deepcopy(FAKE_PAYMENT_METHOD_I))

        assert self.customer
        self.assertEqual(1, self.customer.payment_methods.count())

        payment_method = self.customer.payment_methods.first()

        with patch(
            "tests.PaymentMethodDict.detach", side_effect=mocked_detach, autospec=True
        ) as mock_detach, patch(
            "stripe.PaymentMethod.retrieve",
            return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
            autospec=True,
        ):
            self.assertTrue(payment_method.detach())

        self.assertEqual(0, self.customer.payment_methods.count())
        self.assertIsNone(self.customer.default_payment_method)

        self.assertIsNone(payment_method.customer)

        if sys.version_info >= (3, 6):
            # this mock isn't working on py34, py35, but it's not strictly necessary
            # for the test
            mock_detach.assert_called()

        self.assert_fks(
            payment_method, expected_blank_fks={"djstripe.PaymentMethod.customer"}
        )

        with patch(
            "tests.PaymentMethodDict.detach",
            side_effect=InvalidRequestError(
                message="A source must be attached to a customer to be used "
                "as a `payment_method`",
                param="payment_method",
            ),
            autospec=True,
        ) as mock_detach, patch(
            "stripe.PaymentMethod.retrieve",
            return_value=deepcopy(FAKE_PAYMENT_METHOD_I),
            autospec=True,
        ) as payment_method_retrieve_mock:
            payment_method_retrieve_mock.return_value["customer"] = None

            self.assertFalse(
                payment_method.detach(), "Second call to detach should return false"
            )

    def test_detach_card(self):
        original_detach = PaymentMethodDict.detach

        # "card_" payment methods are deleted after detach
        deleted_card_exception = InvalidRequestError(
            message="No such payment_method: card_xxxx",
            param="payment_method",
            code="resource_missing",
        )

        def mocked_detach(*args, **kwargs):
            return original_detach(*args, **kwargs)

        with patch(
            "stripe.PaymentMethod.retrieve",
            return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
            autospec=True,
        ):
            models.PaymentMethod.sync_from_stripe_data(
                deepcopy(FAKE_CARD_AS_PAYMENT_METHOD)
            )

        assert self.customer
        assert self.customer.payment_methods.count() == 1

        payment_method = self.customer.payment_methods.first()

        self.assertTrue(
            payment_method.id.startswith("card_"), "We expect this to be a 'card_'"
        )

        with patch(
            "tests.PaymentMethodDict.detach", side_effect=mocked_detach, autospec=True
        ) as mock_detach, patch(
            "stripe.PaymentMethod.retrieve",
            return_value=deepcopy(FAKE_CARD_AS_PAYMENT_METHOD),
            autospec=True,
        ):
            self.assertTrue(payment_method.detach())

        assert self.customer.payment_methods.count() == 0
        assert self.customer.default_payment_method is None

        self.assertEqual(
            models.PaymentMethod.objects.filter(id=payment_method.id).count(),
            0,
            "We expect PaymentMethod id = card_* to be deleted",
        )

        if sys.version_info >= (3, 6):
            # this mock isn't working on py34, py35, but it's not strictly necessary
            # for the test
            mock_detach.assert_called()

        with patch(
            "tests.PaymentMethodDict.detach",
            side_effect=InvalidRequestError(
                message="A source must be attached to a customer to be used "
                "as a `payment_method`",
                param="payment_method",
            ),
            autospec=True,
        ) as mock_detach, patch(
            "stripe.PaymentMethod.retrieve",
            side_effect=deleted_card_exception,
            autospec=True,
        ) as payment_method_retrieve_mock:
            payment_method_retrieve_mock.return_value["customer"] = None

            self.assertFalse(
                payment_method.detach(), "Second call to detach should return false"
            )

    def test_sync_null_customer(self):
        payment_method = models.PaymentMethod.sync_from_stripe_data(
            deepcopy(FAKE_PAYMENT_METHOD_I)
        )
        assert payment_method

        self.assertIsNotNone(payment_method.customer)

        # simulate remote detach
        fake_payment_method_no_customer = deepcopy(FAKE_PAYMENT_METHOD_I)
        fake_payment_method_no_customer["customer"] = None

        payment_method = models.PaymentMethod.sync_from_stripe_data(
            fake_payment_method_no_customer
        )
        assert payment_method

        self.assertIsNone(payment_method.customer)

        self.assert_fks(
            payment_method, expected_blank_fks={"djstripe.PaymentMethod.customer"}
        )
