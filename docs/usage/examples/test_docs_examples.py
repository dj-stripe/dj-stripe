from unittest.mock import patch

from django.test import TestCase
from docs.usage.examples import manually_syncing_with_stripe

import djstripe.models


class CheckExamplesTest(TestCase):
	"""
	Sanity check example code
	"""

	@patch("stripe.Product.create", autospec=True)
	def test_manually_sync_data_with_stripe(self, product_create_mock):
		example_product_data = {
			"id": "example_product",
			"object": "product",
			"active": True,
			"name": "Monthly membership base fee",
			"type": "service",
		}

		product_create_mock.return_value = example_product_data

		manually_syncing_with_stripe.example()

		self.assertEqual(
			djstripe.models.Product.objects.last().id, example_product_data["id"]
		)
