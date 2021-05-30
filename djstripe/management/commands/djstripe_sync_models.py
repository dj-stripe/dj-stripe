from typing import List

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from ... import enums, models, settings
from ...models.base import StripeBaseModel


class Command(BaseCommand):
    """Sync models from stripe."""

    help = "Sync models from stripe."

    def add_arguments(self, parser):
        parser.add_argument(
            "args",
            metavar="ModelName",
            nargs="*",
            help="restricts sync to these model names (default is to sync all "
            "supported models)",
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
                    raise CommandError(
                        "Unknown model: {}.{}".format(app_label, model_label)
                    )

                model_list.append(model)
        else:
            model_list = app_config.get_models()

        for model in model_list:
            self.sync_model(model)

    def _should_sync_model(self, model):
        if not issubclass(model, StripeBaseModel):
            return False, "not a StripeModel"

        if model.stripe_class is None:
            return False, "no stripe_class"

        if not hasattr(model.stripe_class, "list"):
            return False, "no stripe_class.list"

        if model is models.UpcomingInvoice:
            return False, "Upcoming Invoices are virtual only"

        if not settings.STRIPE_LIVE_MODE:
            if model is models.ScheduledQueryRun:
                return False, "only available in live mode"

        return True, ""

    def sync_model(self, model):
        model_name = model.__name__

        should_sync, reason = self._should_sync_model(model)
        if not should_sync:
            self.stdout.write(f"Skipping {model}: {reason}")
            return

        self.stdout.write("Syncing {}:".format(model_name))

        count = 0
        try:
            for list_kwargs in self.get_list_kwargs(model):

                if model is models.Account:
                    # special case, since own account isn't returned by Account.api_list
                    stripe_obj = models.Account.stripe_class.retrieve(
                        api_key=settings.STRIPE_SECRET_KEY
                    )
                    count += 1
                    djstripe_obj = model.sync_from_stripe_data(stripe_obj)
                    self.stdout.write(
                        "  id={id}, pk={pk} ({djstripe_obj})".format(
                            id=djstripe_obj.id,
                            pk=djstripe_obj.pk,
                            djstripe_obj=djstripe_obj,
                        )
                    )

                    # syncing BankAccount and Card objects of Stripe Connected Express and Custom Accounts
                    self.sync_external_account_bank_accounts_and_cards(djstripe_obj)

                for stripe_obj in model.api_list(**list_kwargs):
                    count += 1
                    djstripe_obj = model.sync_from_stripe_data(stripe_obj)
                    self.stdout.write(
                        "  id={id}, pk={pk} ({djstripe_obj})".format(
                            id=djstripe_obj.id,
                            pk=djstripe_obj.pk,
                            djstripe_obj=djstripe_obj,
                        )
                    )
                    # syncing BankAccount and Card objects of Stripe Connected Express and Custom Accounts
                    self.sync_external_account_bank_accounts_and_cards(djstripe_obj)

        except Exception as e:
            self.stderr.write(str(e))

        if count == 0:
            self.stdout.write("  (no results)")
        else:
            self.stdout.write(
                "  Synced {count} {model_name}".format(
                    count=count, model_name=model_name
                )
            )

    def get_list_kwargs(self, model):
        """
        Returns a sequence of kwargs dicts to pass to model.api_list

        This allows us to sync models that require parameters to api_list

        :param model:
        :return: Sequence[dict]
        """
        all_list_kwargs = (
            [{"expand": [f"data.{k}" for k in model.expand_fields]}]
            if getattr(models, "expand_fields", [])
            else []
        )
        if model is models.PaymentMethod:
            # special case
            all_list_kwargs.extend(
                (
                    {"customer": stripe_customer.id, "type": "card"}
                    for stripe_customer in models.Customer.api_list()
                )
            )
        elif model is models.SubscriptionItem:
            all_list_kwargs.extend(
                (
                    {"subscription": subscription.id}
                    for subscription in models.Subscription.api_list()
                )
            )
        elif model is models.CountrySpec:
            all_list_kwargs.extend(({"limit": 50},))
        elif not all_list_kwargs:
            all_list_kwargs.append({})

        return all_list_kwargs

    def sync_external_account_bank_accounts_and_cards(self, instance):
        type = getattr(instance, "type", None)
        id = instance.id

        if type in (enums.AccountType.custom, enums.AccountType.express) and isinstance(
            instance, models.Account
        ):
            # fetch all Card and BankAccount objects associated with the instance
            items = models.Account.stripe_class.list_external_accounts(
                id,
                api_key=settings.STRIPE_SECRET_KEY,
            )
            bank_count = 0
            card_count = 0
            for item in items.auto_paging_iter():

                if item.object == "bank_account":
                    model = models.BankAccount
                    bank_count += 1
                elif item.object == "card":
                    model = models.Card
                    card_count += 1

                item_obj = model.sync_from_stripe_data(item)

                self.stdout.write(
                    f"\tSyncing {model._meta.verbose_name} ({instance}): id={item_obj.id}, pk={item_obj.pk}"
                )

            if bank_count + card_count > 0:
                self.stdout.write(
                    f"\tSynced {bank_count} BankAccounts and {card_count} Cards"
                )
