from django.core.management.base import BaseCommand

from ...models import (
	Account, BankAccount, Card, Charge, Customer, Event,
	Invoice, Payout, Plan, Product, Refund, Source, Transfer
)


class Command(BaseCommand):
	"""Set null text fields to empty string to workaround incompatibility with migration 0003 on postgres

	See https://github.com/dj-stripe/dj-stripe/issues/850
	"""

	help = """Set null text fields to empty string to workaround incompatibility with migration 0003 on postgres"""

	def handle(self, *args, **options):

		model_fields = [
			(
				Account,
				(
					"business_name",
					"business_primary_color",
					"business_url",
					"payout_statement_descriptor",
					"product_description",
					"support_url",
				),
			),
			(BankAccount, ("account_holder_name",)),
			(
				Card,
				(
					"address_city",
					"address_country",
					"address_line1",
					"address_line1_check",
					"address_line2",
					"address_state",
					"address_zip",
					"address_zip_check",
					"country",
					"cvc_check",
					"dynamic_last4",
					"fingerprint",
					"name",
					"tokenization_method",
				),
			),
			(
				Charge,
				(
					"failure_code",
					"failure_message",
					"receipt_email",
					"receipt_number",
					"statement_descriptor",
					"transfer_group",
				),
			),
			(Customer, ("business_vat_id", "currency", "email")),
			(Event, ("idempotency_key", "request_id")),
			(Invoice, ("hosted_invoice_url", "invoice_pdf", "number", "statement_descriptor")),
			(Payout, ("failure_code", "failure_message", "statement_descriptor")),
			(Plan, ("aggregate_usage", "billing_scheme", "nickname")),
			(Product, ("caption", "statement_descriptor", "unit_label")),
			(Refund, ("failure_reason", "reason", "receipt_number")),
			(Source, ("currency", "statement_descriptor")),
			(Transfer, ("transfer_group",)),
		]

		for model, fields in model_fields:
			for field in fields:
				self.stdout.write("updating {}.{}".format(model.__name__, field))
				filter_param = {"{}__isnull".format(field): True}
				update_param = {field: ""}
				model.objects.filter(**filter_param).update(**update_param)
