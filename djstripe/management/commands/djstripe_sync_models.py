"""Module for the djstripe_sync_model management command to sync
all Stripe objects to the local db.

Invoke like so:
    1) To sync all Objects:
        python manage.py djstripe_sync_models

    2) To only sync Stripe Accounts:
        python manage.py djstripe_sync_models Account
"""
from typing import List

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from ... import enums, models
from ...models.base import StripeBaseModel
from ...settings import djstripe_settings

# TODO Improve performance using multiprocessing


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

    def sync_model(self, model):  # noqa: C901
        model_name = model.__name__

        should_sync, reason = self._should_sync_model(model)
        if not should_sync:
            self.stderr.write(f"Skipping {model}: {reason}")
            return

        self.stdout.write("Syncing {}:".format(model_name))

        count = 0
        try:
            # todo convert get_list_kwargs into a generator to make the code memory effecient.
            for list_kwargs in self.get_list_kwargs(model):
                stripe_account = list_kwargs.get("stripe_account", "")

                if (
                    model is models.Account
                    and stripe_account == models.Account.get_default_account().id
                ):
                    # special case, since own account isn't returned by Account.api_list
                    stripe_obj = models.Account.stripe_class.retrieve(
                        api_key=djstripe_settings.STRIPE_SECRET_KEY
                    )

                    djstripe_obj = model.sync_from_stripe_data(stripe_obj)
                    self.stdout.write(
                        f"  id={djstripe_obj.id}, pk={djstripe_obj.pk} ({djstripe_obj} on {stripe_account})"
                    )

                    # syncing BankAccount and Card objects of Stripe Connected Express and Custom Accounts
                    self.sync_bank_accounts_and_cards(
                        djstripe_obj, stripe_account=stripe_account
                    )
                    count += 1

                try:
                    for stripe_obj in model.api_list(**list_kwargs):
                        # Skip model instances that throw an error
                        try:
                            djstripe_obj = model.sync_from_stripe_data(stripe_obj)
                            self.stdout.write(
                                f"  id={djstripe_obj.id}, pk={djstripe_obj.pk} ({djstripe_obj} on {stripe_account})"
                            )
                            # syncing BankAccount and Card objects of Stripe Connected Express and Custom Accounts
                            self.sync_bank_accounts_and_cards(
                                djstripe_obj, stripe_account=stripe_account
                            )
                            count += 1
                        except Exception as e:
                            self.stderr.write(f"Skipping {stripe_obj.get('id')}: {e}")

                            continue
                except Exception as e:
                    self.stderr.write(f"Skipping: {e}")

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

    @classmethod
    def get_stripe_account(cls, *args, **kwargs):
        """Get set of all stripe account ids including the Platform Acccount"""
        accs_set = set()

        # special case, since own account isn't returned by Account.api_list
        stripe_platform_obj = models.Account.stripe_class.retrieve(
            api_key=djstripe_settings.STRIPE_SECRET_KEY
        )
        accs_set.add(stripe_platform_obj.id)

        for stripe_connected_obj in models.Account.api_list(**kwargs):
            accs_set.add(stripe_connected_obj.id)

        return accs_set

    @staticmethod
    def get_default_list_kwargs(model, accounts_set):
        """Returns default sequence of kwargs to sync
        all Stripe Accounts"""

        if getattr(model, "expand_fields", []):
            default_list_kwargs = [
                {
                    "expand": [f"data.{k}" for k in model.expand_fields],
                    "stripe_account": account,
                }
                for account in accounts_set
            ]

        else:
            default_list_kwargs = [
                {"stripe_account": account} for account in accounts_set
            ]

        return default_list_kwargs

    @staticmethod
    def get_list_kwargs_pm(default_list_kwargs):
        """Returns sequence of kwrags to sync Payment Methods for
        all Stripe Accounts"""

        all_list_kwargs = []
        payment_method_types = enums.PaymentMethodType.__members__

        for def_kwarg in default_list_kwargs:
            stripe_account = def_kwarg.get("stripe_account")
            for stripe_customer in models.Customer.api_list(
                stripe_account=stripe_account
            ):
                for type in payment_method_types:
                    all_list_kwargs.append(
                        {"customer": stripe_customer.id, "type": type, **def_kwarg}
                    )

        return all_list_kwargs

    @staticmethod
    def get_list_kwargs_si(default_list_kwargs):
        """Returns sequence of kwrags to sync Subscription Items for
        all Stripe Accounts"""

        all_list_kwargs = []
        for def_kwarg in default_list_kwargs:
            stripe_account = def_kwarg.get("stripe_account")
            for subscription in models.Subscription.api_list(
                stripe_account=stripe_account
            ):
                all_list_kwargs.append({"subscription": subscription.id, **def_kwarg})
        return all_list_kwargs

    @staticmethod
    def get_list_kwargs_country_spec(default_list_kwargs):
        """Returns sequence of kwrags to sync Country Specs for
        all Stripe Accounts"""

        all_list_kwargs = []
        for def_kwarg in default_list_kwargs:
            all_list_kwargs.append({"limit": 50, **def_kwarg})

        return all_list_kwargs

    @staticmethod
    def get_list_kwargs_trr(default_list_kwargs):
        """Returns sequence of kwrags to sync Transfer Reversals for
        all Stripe Accounts"""
        all_list_kwargs = []
        for def_kwarg in default_list_kwargs:
            stripe_account = def_kwarg.get("stripe_account")
            for transfer in models.Transfer.api_list(stripe_account=stripe_account):
                all_list_kwargs.append({"id": transfer.id, **def_kwarg})

        return all_list_kwargs

    @staticmethod
    def get_list_kwargs_fee_refund(default_list_kwargs):
        """Returns sequence of kwrags to sync Application Fee Refunds for
        all Stripe Accounts"""
        all_list_kwargs = []
        for def_kwarg in default_list_kwargs:
            stripe_account = def_kwarg.get("stripe_account")
            for fee in models.ApplicationFee.api_list(stripe_account=stripe_account):
                all_list_kwargs.append({"id": fee.id, **def_kwarg})

        return all_list_kwargs

    @staticmethod
    def get_list_kwargs_tax_id(default_list_kwargs):
        """Returns sequence of kwrags to sync Tax Ids for
        all Stripe Accounts"""
        all_list_kwargs = []
        for def_kwarg in default_list_kwargs:
            stripe_account = def_kwarg.get("stripe_account")
            for customer in models.Customer.api_list(stripe_account=stripe_account):
                all_list_kwargs.append({"id": customer.id, **def_kwarg})

        return all_list_kwargs

    @staticmethod
    def get_list_kwargs_sis(default_list_kwargs):
        """Returns sequence of kwrags to sync Usage Record Summarys for
        all Stripe Accounts"""
        all_list_kwargs = []
        for def_kwarg in default_list_kwargs:
            stripe_account = def_kwarg.get("stripe_account")
            for subscription in models.Subscription.api_list(
                stripe_account=stripe_account
            ):
                for subscription_item in models.SubscriptionItem.api_list(
                    subscription=subscription.id, stripe_account=stripe_account
                ):
                    all_list_kwargs.append({"id": subscription_item.id, **def_kwarg})

        return all_list_kwargs

    # todo handle supoorting double + nested fields like data.invoice.subscriptions.customer etc?
    def get_list_kwargs(self, model):
        """
        Returns a sequence of kwargs dicts to pass to model.api_list

        This allows us to sync models that require parameters to api_list

        :param model:
        :return: Sequence[dict]
        """

        list_kwarg_handlers_dict = {
            "PaymentMethod": self.get_list_kwargs_pm,
            "SubscriptionItem": self.get_list_kwargs_si,
            "CountrySpec": self.get_list_kwargs_country_spec,
            "TransferReversal": self.get_list_kwargs_trr,
            "ApplicationFeeRefund": self.get_list_kwargs_fee_refund,
            "TaxId": self.get_list_kwargs_tax_id,
            "UsageRecordSummary": self.get_list_kwargs_sis,
        }

        # get all Stripe Accounts for the given platform account.
        # note that we need to fetch from Stripe as we have no way of knowing that the ones in the local db are up to date
        # as this can also be the first time the user runs sync.
        accs_set = self.get_stripe_account()

        default_list_kwargs = self.get_default_list_kwargs(model, accs_set)

        handler = list_kwarg_handlers_dict.get(
            model.__name__, lambda _: default_list_kwargs
        )

        return handler(default_list_kwargs)

    def sync_bank_accounts_and_cards(self, instance, *, stripe_account):
        """
        Syncs Bank Accounts and Cards for both customers and all external accounts
        """
        type = getattr(instance, "type", None)
        kwargs = {
            "id": instance.id,
            "api_key": djstripe_settings.STRIPE_SECRET_KEY,
            "stripe_account": stripe_account,
        }

        if type in (enums.AccountType.custom, enums.AccountType.express) and isinstance(
            instance, models.Account
        ):

            # fetch all Card and BankAccount objects associated with the instance
            items = models.Account.stripe_class.list_external_accounts(
                **kwargs
            ).auto_paging_iter()

            self.start_sync(items, instance)
        elif isinstance(instance, models.Customer):
            for object in ("card", "bank_account"):
                kwargs["object"] = object

                # fetch all Card and BankAccount objects associated with the instance
                items = models.Customer.stripe_class.list_sources(
                    **kwargs
                ).auto_paging_iter()

                self.start_sync(items, instance)

    def start_sync(self, items, instance):
        bank_count = 0
        card_count = 0
        for item in items:

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
