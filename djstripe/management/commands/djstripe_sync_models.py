from typing import List

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from ... import models, settings


class Command(BaseCommand):
	"""Sync models from stripe."""

	help = "Sync models from stripe."

	def add_arguments(self, parser):
		parser.add_argument(
			"args",
			metavar="ModelName",
			nargs="*",
			help="restricts sync to these model names (default is to sync all supported models)",
		)

	def handle(self, *args, **options):
		app_label = "djstripe"
		app_config = apps.get_app_config(app_label)
		model_list = []  # type: List[models.StripeModel]

		if args:
			for model_label in args:
				try:
					model = app_config.get_model(model_label)
				except LookupError:
					raise CommandError("Unknown model: {}.{}".format(app_label, model_label))

				model_list.append(model)
		else:
			model_list = app_config.get_models()

		for model in model_list:
			self.sync_model(model)

	def sync_model(self, model):
		model_name = model.__name__

		if not issubclass(model, models.StripeModel):
			print("Skipping {} (not a StripeModel)".format(model_name))
			return

		if model.stripe_class is None:
			print("Skipping {} (no stripe_class)".format(model_name))
			return

		if not hasattr(model.stripe_class, "list"):
			print("Skipping {} (no stripe_class.list)".format(model_name))
			return

		print("Syncing {}:".format(model_name))

		try:
			count = 0

			if model is models.Account:
				# special case, since own account isn't returned by Account.api_list
				stripe_obj = models.Account.stripe_class.retrieve(
					api_key=settings.STRIPE_SECRET_KEY
				)
				count += 1
				djstripe_obj = model.sync_from_stripe_data(stripe_obj)
				print(
					"  id={id}, pk={pk} ({djstripe_obj})".format(
						id=djstripe_obj.id, pk=djstripe_obj.pk, djstripe_obj=djstripe_obj
					)
				)

			for stripe_obj in model.api_list():
				count += 1
				djstripe_obj = model.sync_from_stripe_data(stripe_obj)
				print(
					"  id={id}, pk={pk} ({djstripe_obj})".format(
						id=djstripe_obj.id, pk=djstripe_obj.pk, djstripe_obj=djstripe_obj
					)
				)

			if count == 0:
				print("  (no results)")
			else:
				print("  Synced {count} {model_name}".format(count=count, model_name=model_name))

		except Exception as e:
			print(e)
