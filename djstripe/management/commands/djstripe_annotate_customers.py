"""
annotate_customers command.
"""
import datetime 

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist

from ...models import Customer
from ...settings import get_subscriber_model

class Command(BaseCommand):
	"""Annotate customer instances within the Stripe account itself."""

	help = "Annotate customer instances within the Stripe account itself"

	def handle(self, *args, **options):
		"""Annotate customer accounts within remote Stripe environments by
		adding or changing the djstripe_subscriber value within the account's metadata
		field, to the subscriber.id value, if and when a subscriber/customer pair does exist, 
		but the customer information isn't availably locally and the subscriber information isn't
		attached to the customer account information remotely."""
		
		for customer in Customer.api_list():
			print("Annotating Customer: %s " % customer.id)

			try:
				dj_subscriber = get_subscriber_model().objects.get(email=customer.email)
				if dj_subscriber:
					customer.metadata = {} or customer.metadata
					customer.metadata['djstripe_subscriber'] = dj_subscriber.id 
					customer.metadata['updated'] = datetime.datetime.now()
					customer.save()
			except ObjectDoesNotExist as e:
				# these will be created by the djstripe_init_customers command 
				print("%s %s" % (customer.email, e))
				continue 
