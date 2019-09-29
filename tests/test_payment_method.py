"""
dj-stripe PaymenthMethod Model Tests.
"""
import sys
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from stripe.error import InvalidRequestError

from djstripe.models import PaymentMethod

from . import (
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CUSTOMER,
    FAKE_PAYMENT_METHOD_I,
    AssertStripeFksMixin,
    PaymentMethodDict,
    default_account,
)


class PaymentMethodTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        self.account = default_account()
        self.user = get_user_model().objects.create_user(
            username="testuser", email="djstripe@example.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

    # TODO - these should use autospec=True with stripe.PaymentMethod.attach,
    #  but it's failing for some reason with:
    #  TypeError: got an unexpected keyword argument 'customer'

    @patch("stripe.PaymentMethod.attach", return_value=deepcopy(FAKE_PAYMENT_METHOD_I))
    def test_attach(self, attach_mock):
        payment_method = PaymentMethod.attach(
            FAKE_PAYMENT_METHOD_I["id"], customer=FAKE_CUSTOMER["id"]
        )

        self.assert_fks(
            payment_method,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
            },
        )

    @patch("stripe.PaymentMethod.attach", return_value=deepcopy(FAKE_PAYMENT_METHOD_I))
    def test_attach_obj(self, attach_mock):
        pm = PaymentMethod.sync_from_stripe_data(FAKE_PAYMENT_METHOD_I)

        payment_method = PaymentMethod.attach(pm, customer=self.customer)

        self.assert_fks(
            payment_method,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
            },
        )

    @patch("stripe.PaymentMethod.attach", return_value=deepcopy(FAKE_PAYMENT_METHOD_I))
    def test_attach_synced(self, attach_mock):
        fake_payment_method = deepcopy(FAKE_PAYMENT_METHOD_I)
        fake_payment_method["customer"] = None

        payment_method = PaymentMethod.sync_from_stripe_data(fake_payment_method)

        self.assert_fks(
            payment_method, expected_blank_fks={"djstripe.PaymentMethod.customer"}
        )

        payment_method = PaymentMethod.attach(
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
            PaymentMethod.sync_from_stripe_data(deepcopy(FAKE_PAYMENT_METHOD_I))

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
            PaymentMethod.sync_from_stripe_data(deepcopy(FAKE_CARD_AS_PAYMENT_METHOD))

        self.assertEqual(1, self.customer.payment_methods.count())

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

        self.assertEqual(0, self.customer.payment_methods.count())
        self.assertIsNone(self.customer.default_payment_method)

        self.assertEqual(
            PaymentMethod.objects.filter(id=payment_method.id).count(),
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
        payment_method = PaymentMethod.sync_from_stripe_data(
            deepcopy(FAKE_PAYMENT_METHOD_I)
        )

        self.assertIsNotNone(payment_method.customer)

        # simulate remote detach
        fake_payment_method_no_customer = deepcopy(FAKE_PAYMENT_METHOD_I)
        fake_payment_method_no_customer["customer"] = None

        payment_method = PaymentMethod.sync_from_stripe_data(
            fake_payment_method_no_customer
        )

        self.assertIsNone(payment_method.customer)

        self.assert_fks(
            payment_method, expected_blank_fks={"djstripe.PaymentMethod.customer"}
        )
