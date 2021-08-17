from typing import List

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from ... import enums, models
from ...models.base import StripeBaseModel
from ...settings import djstripe_settings


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
            if model in (
                models.ApplicationFeeRefund,
                models.TransferReversal,
                models.TaxId,
                models.UsageRecordSummary,
            ):
                return True, ""
            return False, "no stripe_class.list"

        if model is models.UpcomingInvoice:
            return False, "Upcoming Invoices are virtual only"

        if not djstripe_settings.STRIPE_LIVE_MODE:
            if model is models.ScheduledQueryRun:
                return False, "only available in live mode"

        return True, ""

    def sync_model(self, model):
        model_name = model.__name__

        should_sync, reason = self._should_sync_model(model)
        if not should_sync:
            self.stderr.write(f"Skipping {model}: {reason}")
            return

        self.stdout.write("Syncing {}:".format(model_name))

        count = 0
        try:
            for list_kwargs in self.get_list_kwargs(model):

                if model is models.Account:
                    # special case, since own account isn't returned by Account.api_list
                    stripe_obj = models.Account.stripe_class.retrieve(
                        api_key=djstripe_settings.STRIPE_SECRET_KEY
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
                    self.sync_bank_accounts_and_cards(djstripe_obj)

                for stripe_obj in model.api_list(**list_kwargs):
                    # Skip model instances that throw an error
                    try:
                        djstripe_obj = model.sync_from_stripe_data(stripe_obj)
                        self.stdout.write(
                            "  id={id}, pk={pk} ({djstripe_obj})".format(
                                id=djstripe_obj.id,
                                pk=djstripe_obj.pk,
                                djstripe_obj=djstripe_obj,
                            )
                        )
                        # syncing BankAccount and Card objects of Stripe Connected Express and Custom Accounts
                        self.sync_bank_accounts_and_cards(djstripe_obj)
                        count += 1
                    except Exception as e:
                        self.stderr.write(f"Skipping {stripe_obj.get('id')}: {e}")
                        continue

            if count == 0:
                self.stdout.write("  (no results)")
            else:
                self.stdout.write(
                    "  Synced {count} {model_name}".format(
                        count=count, model_name=model_name
                    )
                )

        except Exception as e:
            self.stderr.write(str(e))

    # todo Handle syncing data for connected accounts as well. # https://stripe.com/docs/api/accounts/list
    # ! Will need to re-run with different values of stripe_account
    # todo handle supoorting double + nested fields like data.invoice.subscriptions.customer etc?
    def get_list_kwargs(self, model):
        """
        Returns a sequence of kwargs dicts to pass to model.api_list

        This allows us to sync models that require parameters to api_list

        :param model:
        :return: Sequence[dict]
        """
        all_list_kwargs = (
            [{"expand": [f"data.{k}" for k in model.expand_fields]}]
            if getattr(model, "expand_fields", [])
            else [{}]
        )

        if model is models.PaymentMethod:
            # special case
            all_list_kwargs = [
                {"customer": stripe_customer.id, "type": "card", **all_list_kwargs[0]}
                for stripe_customer in models.Customer.api_list()
            ]

        elif model is models.SubscriptionItem:
            all_list_kwargs = [
                {"subscription": subscription.id, **all_list_kwargs[0]}
                for subscription in models.Subscription.api_list()
            ]

        elif model is models.CountrySpec:
            all_list_kwargs.extend(({"limit": 50},))

        elif model is models.TransferReversal:
            all_list_kwargs = [
                {"id": transfer.id, **all_list_kwargs[0]}
                for transfer in models.Transfer.api_list()
            ]

        elif model is models.ApplicationFeeRefund:
            all_list_kwargs = [
                {"id": fee.id, **all_list_kwargs[0]}
                for fee in models.ApplicationFee.api_list()
            ]
        elif model is models.TaxId:
            all_list_kwargs = [
                {"id": customer.id, **all_list_kwargs[0]}
                for customer in models.Customer.api_list()
            ]

        elif model is models.UsageRecordSummary:
            all_list_kwargs = [
                {"id": subscription_item.id, **all_list_kwargs[0]}
                for subscription in models.Subscription.api_list()
                for subscription_item in models.SubscriptionItem.api_list(
                    subscription=subscription.id
                )
            ]

        elif not all_list_kwargs:
            all_list_kwargs.append({})

        return all_list_kwargs

    def sync_bank_accounts_and_cards(self, instance):
        """
        Syncs Bank Accounts and Cards for both customers and all external accounts
        """
        type = getattr(instance, "type", None)
        kwargs = {
            "id": instance.id,
            "api_key": djstripe_settings.STRIPE_SECRET_KEY,
        }

        if type in (enums.AccountType.custom, enums.AccountType.express) and isinstance(
            instance, models.Account
        ):

            # fetch all Card and BankAccount objects associated with the instance
            items = models.Account.stripe_class.list_external_accounts(**kwargs)

            self.start_sync(items, instance)
        elif isinstance(instance, models.Customer):
            for object in ("card", "bank_account"):
                kwargs["object"] = object

                # fetch all Card and BankAccount objects associated with the instance
                items = models.Customer.stripe_class.list_sources(**kwargs)

                self.start_sync(items, instance)

    def start_sync(self, items, instance):
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
