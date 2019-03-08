"""
dj-stripe Bank Account Model Tests.
"""
from copy import deepcopy

from django.test import TestCase

from djstripe.models import BankAccount

from . import AssertStripeFksMixin, FAKE_BANK_ACCOUNT


class BankAccountTest(AssertStripeFksMixin, TestCase):

	def test_str(self):
		fake_bank_account = deepcopy(FAKE_BANK_ACCOUNT)
		bank_account = BankAccount.sync_from_stripe_data(bank_account)

		self.assertEqual(
			"<{holder} in {bank} ({status})".format(
				holder=fake_bank_account["account_holder_name"],
				bank=fake_bank_account["bank_name"],
				status=fake_bank_account["status"],
			),
			str(bank_account),
		)
