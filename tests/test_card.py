"""
.. module:: dj-stripe.tests.test_card
   :synopsis: dj-stripe Card Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from copy import deepcopy

from django.core.exceptions import ValidationError
from django.test import TestCase

from mock import patch

from djstripe.models import Account, Card

from . import FAKE_CARD_III


class CardTest(TestCase):

    def setUp(self):
        self.account = Account.objects.create()

    @patch("djstripe.models.Account.get_default_account")
    def test_attach_objects_hook_without_customer(self, default_account_mock):
        default_account_mock.return_value = self.account

        with self.assertRaisesMessage(ValidationError, "A customer was not attached to this card."):
            Card.sync_from_stripe_data(deepcopy(FAKE_CARD_III))
