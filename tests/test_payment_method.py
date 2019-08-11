"""
dj-stripe PaymenthMethod Model Tests.
"""
from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from tests import (
    FAKE_CUSTOMER,
    FAKE_PAYMENT_METHOD_I,
    AssertStripeFksMixin,
    default_account,
)

from djstripe.models import PaymentMethod


class PaymentMethodTest(AssertStripeFksMixin, TestCase):
    def setUp(self):
        self.account = default_account()
        self.user = get_user_model().objects.create_user(
            username="testuser", email="djstripe@example.com"
        )
        self.customer = FAKE_CUSTOMER.create_for_user(self.user)

    # TODO - this should use autospec=True, but it's failing for some reason
    #   with unexpected keyword argument "customer"
    @patch("stripe.PaymentMethod.attach", return_value=deepcopy(FAKE_PAYMENT_METHOD_I))
    def test_attach(self, attach_mock):
        payment_method = PaymentMethod.attach(
            FAKE_PAYMENT_METHOD_I["id"], stripe_customer=FAKE_CUSTOMER
        )

        self.assert_fks(
            payment_method,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
            },
        )

    # TODO - this should use autospec=True, but it's failing for some reason
    #   with unexpected keyword argument "customer"
    @patch("stripe.PaymentMethod.attach", return_value=deepcopy(FAKE_PAYMENT_METHOD_I))
    def test_attach_synced(self, attach_mock):
        fake_payment_method = deepcopy(FAKE_PAYMENT_METHOD_I)
        fake_payment_method["customer"] = None

        payment_method = PaymentMethod.sync_from_stripe_data(fake_payment_method)

        self.assert_fks(
            payment_method, expected_blank_fks={"djstripe.PaymentMethod.customer"}
        )

        payment_method = PaymentMethod.attach(
            payment_method.id, stripe_customer=FAKE_CUSTOMER
        )

        self.assert_fks(
            payment_method,
            expected_blank_fks={
                "djstripe.Customer.coupon",
                "djstripe.Customer.default_payment_method",
            },
        )
