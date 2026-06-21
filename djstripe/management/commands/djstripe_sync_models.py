"""Module for the djstripe_sync_model management command to sync
all Stripe objects to the local db.

By default this syncs every secret/restricted API key found in the database as
well as the keys defined in your Django settings (STRIPE_SECRET_KEY,
STRIPE_TEST_SECRET_KEY and STRIPE_LIVE_SECRET_KEY). This means it works with
environment-variable-only setups, without first adding keys via the admin.

Invoke like so:
    1) To sync all Objects for all API keys:
        python manage.py djstripe_sync_models

    2) To sync all Objects only for sk_test_XXX API key:
        python manage.py djstripe_sync_models --api-keys sk_test_XXX

    3) To sync all Objects only for sk_test_XXX and sk_test_YYY API keys:
        python manage.py djstripe_sync_models --api-keys sk_test_XXX sk_test_XXX
                                    OR
        python manage.py djstripe_sync_models --api-keys sk_test_XXX --api-keys sk_test_XXX

    4) To only sync Stripe Accounts for all API keys:
        python manage.py djstripe_sync_models Account

    5) To only sync Stripe Accounts for sk_test_XXX API key:
        python manage.py djstripe_sync_models Account --api-keys sk_test_XXX

    6) To only sync Stripe Accounts for sk_test_XXX and sk_test_YYY API keys:
        python manage.py djstripe_sync_models Account --api-keys sk_test_XXX sk_test_YYY

    7) To only sync Stripe Accounts and Charges for sk_test_XXX and sk_test_YYY API keys:
        python manage.py djstripe_sync_models Account Charge --api-keys sk_test_XXX sk_test_YYY
"""

import argparse

from django.apps import apps
from django.core.exceptions import FieldDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import models as django_models

from ... import enums, models
from ...enums import APIKeyType
from ...exceptions import InvalidStripeAPIKey
from ...models.api import get_api_key_details_by_prefix, redact_api_key
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
            help=(
                "restricts sync to these model names (default is to sync all "
                "supported models)"
            ),
        )
        # Named (optional) arguments
        parser.add_argument(
            "--api-keys",
            metavar="ApiKeys",
            nargs="*",
            type=str,
            action="extend",
            help="Specify the api_keys you would like to perform this sync for.",
        )
        parser.add_argument(
            "--fail-on-error",
            action=argparse.BooleanOptionalAction,
            default=None,
            help=(
                "Exit with a non-zero status if any model/key or object fails to"
                " sync. Defaults to enabled when run from the command line (so"
                " cron/CI can detect failures) and disabled when invoked"
                " programmatically via call_command()."
            ),
        )

    def handle(self, *args, api_keys: list[str], fail_on_error=None, **options):
        app_label = "djstripe"
        app_config = apps.get_app_config(app_label)
        model_list: list[models.StripeModel] = []

        # When --fail-on-error / --no-fail-on-error isn't passed explicitly,
        # default to failing loudly on the command line (so cron/CI can detect
        # problems) but stay quiet when invoked programmatically via
        # call_command(), where a raised CommandError would become an unhandled
        # exception in the caller (e.g. the admin "Sync All Instances" action).
        if fail_on_error is None:
            fail_on_error = self._called_from_command_line

        if args:
            for model_label in args:
                try:
                    model = app_config.get_model(model_label)
                except LookupError:
                    raise CommandError(f"Unknown model: {app_label}.{model_label}")

                model_list.append(model)
        else:
            model_list = app_config.get_models()

        api_keys = self.get_api_keys(api_keys)
        if not api_keys:
            self.stderr.write(
                "You don't have any API Keys in the database or in your settings."
                " Did you forget to add them?"
            )
            return

        # Count (model, api_key) pairs that failed to sync cleanly so we can
        # surface a summary and exit non-zero, without aborting the whole run on
        # the first error.
        failed_syncs = 0
        for model in model_list:
            for api_key in api_keys:
                if not self.sync_model(model, api_key=api_key):
                    failed_syncs += 1

        if failed_syncs:
            message = f"{failed_syncs} model/key sync(s) failed; see the errors above."
            self.stderr.write(self.style.ERROR(message))
            if fail_on_error:
                raise CommandError(message)

    def get_api_keys(self, api_keys: list[str] | None) -> list[str]:
        """
        Resolve the secret API keys to sync.

        If keys are passed explicitly (via --api-keys), they are validated and
        used as-is, whether or not they exist in the database. Otherwise, every
        secret/restricted key in the database is used, merged with the keys
        defined in the Django settings (so environment-variable-only setups work
        without first adding keys to the admin).
        """
        if api_keys:
            for api_key in api_keys:
                try:
                    get_api_key_details_by_prefix(api_key)
                except InvalidStripeAPIKey as e:
                    raise CommandError(str(e))
            return api_keys

        secrets = list(
            models.APIKey.objects.filter(
                type__in=[APIKeyType.secret, APIKeyType.restricted]
            ).values_list("secret", flat=True)
        )
        for secret in djstripe_settings.get_api_keys():
            if secret not in secrets:
                secrets.append(secret)

        return secrets

    def _should_sync_model(self, model):
        if not issubclass(model, StripeBaseModel):
            return False, "not a StripeModel"

        if model.stripe_class is None:
            return False, "no stripe_class"

        if not hasattr(model.stripe_class, "list"):
            if model in (
                models.ApplicationFeeRefund,
                models.LineItem,
                models.TransferReversal,
                models.TaxId,
            ):
                return True, ""
            return False, "no stripe_class.list"

        if model is models.UpcomingInvoice:
            return False, "Upcoming Invoices are virtual only"

        if not djstripe_settings.STRIPE_LIVE_MODE:
            if model is models.ScheduledQueryRun:
                return False, "only available in live mode"

        return True, ""

    def sync_model(self, model, api_key: str) -> bool:
        """Sync a single model for a single API key.

        Returns True if the model synced without any errors, and False if the
        whole (model, api_key) sync failed or any individual object failed to
        sync. Per-object errors are reported and counted but don't abort the
        run. KeyboardInterrupt/SystemExit are never swallowed.
        """
        model_name = model.__name__

        should_sync, _ = self._should_sync_model(model)
        if not should_sync:
            # Skipping a model that isn't syncable is expected, not a failure.
            return True

        api_key_repr = redact_api_key(api_key)
        self.stdout.write(f"Syncing {model_name} for key {api_key_repr}:")

        count = 0
        object_errors = 0
        try:
            # todo convert get_list_kwargs into a generator to make the code memory effecient.
            for list_kwargs in self.get_list_kwargs(model, api_key=api_key):
                stripe_account = list_kwargs.get("stripe_account", "")

                if (
                    model is models.Account
                    and stripe_account
                    == models.Account.get_default_account(api_key=api_key).id
                ):
                    # special case, since own account isn't returned by Account.api_list
                    stripe_obj = models.Account.stripe_class.retrieve(
                        api_key=api_key,
                        stripe_version=djstripe_settings.STRIPE_API_VERSION,
                    )

                    djstripe_obj = model.sync_from_stripe_data(
                        stripe_obj, api_key=api_key
                    )
                    self.stdout.write(
                        f"  id={djstripe_obj.id},"
                        f" pk={djstripe_obj.pk} ({djstripe_obj} on {stripe_account} for"
                        f" {api_key_repr})"
                    )

                    # syncing BankAccount and Card objects of Stripe Connected Express and Custom Accounts
                    self.sync_bank_accounts_and_cards(
                        djstripe_obj,
                        stripe_account=stripe_account,
                        api_key=api_key,
                    )
                    count += 1

                try:
                    for stripe_obj in model.api_list(**list_kwargs):
                        # Skip (but count) model instances that throw an error,
                        # so a single bad object doesn't abort the whole sync.
                        try:
                            djstripe_obj = model.sync_from_stripe_data(
                                stripe_obj, api_key=api_key
                            )
                            self.stdout.write(
                                f"  id={djstripe_obj.id} ({djstripe_obj} on"
                                f" {stripe_account} for {api_key_repr})"
                            )
                            # syncing BankAccount and Card objects of Stripe Connected Express and Custom Accounts
                            self.sync_bank_accounts_and_cards(
                                djstripe_obj,
                                stripe_account=stripe_account,
                                api_key=api_key,
                            )
                            count += 1
                        except (KeyboardInterrupt, SystemExit):
                            raise
                        except Exception as e:
                            object_errors += 1
                            self.stderr.write(
                                self.style.ERROR(
                                    f"  Error syncing {stripe_obj.get('id')}: {e!r}"
                                )
                            )

                            continue
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception as e:
                    object_errors += 1
                    self.stderr.write(
                        self.style.ERROR(f"  Error listing {model_name}: {e!r}")
                    )

            if count == 0:
                self.stdout.write("  (no results)")
            else:
                self.stdout.write(f"  Synced {count} {model_name} for {api_key_repr}")

            if object_errors:
                self.stderr.write(
                    self.style.ERROR(
                        f"  {object_errors} {model_name} object(s) failed to sync"
                        f" for {api_key_repr}"
                    )
                )

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            # A hard failure syncing this (model, api_key) pair (e.g. an auth
            # error or unexpected exception). Report it with the exception so
            # callers can tell a real failure apart from "no data".
            self.stderr.write(
                self.style.ERROR(
                    f"Failed syncing {model_name} for {api_key_repr}: {e!r}"
                )
            )
            return False

        return object_errors == 0

    @classmethod
    def get_stripe_account(cls, api_key: str, *args, **kwargs):
        """Get set of all stripe account ids including the Platform Acccount"""
        accs_set = set()

        # special case, since own account isn't returned by Account.api_list
        stripe_platform_obj = models.Account.stripe_class.retrieve(
            api_key=api_key,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
        )
        accs_set.add(stripe_platform_obj.id)
        accs_set.update(
            obj.id for obj in models.Account.api_list(api_key=api_key, **kwargs)
        )

        return accs_set

    # todo simplfy this code by spliting into 1-2 functions
    @staticmethod
    def get_default_list_kwargs(model, accounts_set, api_key: str):
        """Returns default sequence of kwargs to sync
        all Stripe Accounts"""
        expand = []

        try:
            # get all forward and reverse relations for given cls
            for field in model.expand_fields:
                # add expand_field on the current model
                expand.append(f"data.{field}")

                try:
                    field_inst = model._meta.get_field(field)

                    # get expand_fields on Forward FK and OneToOneField relations on the current model
                    if isinstance(
                        field_inst,
                        (django_models.ForeignKey, django_models.OneToOneField),
                    ):
                        try:
                            for (
                                related_model_expand_field
                            ) in field_inst.related_model.expand_fields:
                                # add expand_field on the current model
                                expand.append(
                                    f"data.{field}.{related_model_expand_field}"
                                )

                                related_model_expand_field_inst = (
                                    field_inst.related_model._meta.get_field(
                                        related_model_expand_field
                                    )
                                )

                                # get expand_fields on Forward FK and OneToOneField relations on the current model
                                if isinstance(
                                    related_model_expand_field_inst,
                                    (
                                        django_models.ForeignKey,
                                        django_models.OneToOneField,
                                    ),
                                ):
                                    try:
                                        # need to prepend "field_name." to each of the entry in the expand_fields list
                                        related_model_expand_fields = map(
                                            lambda i: (
                                                f"data.{field_inst.name}.{related_model_expand_field}.{i}"
                                            ),
                                            related_model_expand_field_inst.related_model.expand_fields,
                                        )

                                        expand = [
                                            *expand,
                                            *related_model_expand_fields,
                                        ]
                                    except AttributeError:
                                        continue
                        except AttributeError:
                            continue
                except FieldDoesNotExist:
                    pass
        except AttributeError:
            pass

        if expand:
            default_list_kwargs = [
                {
                    "expand": expand,
                    "stripe_account": account,
                    "api_key": api_key,
                }
                for account in accounts_set
            ]

        else:
            default_list_kwargs = [
                {
                    "stripe_account": account,
                    "api_key": api_key,
                }
                for account in accounts_set
            ]

        return default_list_kwargs

    @staticmethod
    def get_list_kwargs_il(default_list_kwargs):
        """Returns sequence of kwargs to sync Line Items for
        all Stripe Accounts"""

        all_list_kwargs = []

        for def_kwarg in default_list_kwargs:
            stripe_account = def_kwarg.get("stripe_account")
            api_key = def_kwarg.get("api_key")
            for stripe_invoice in models.Invoice.api_list(
                stripe_account=stripe_account, api_key=api_key
            ):
                all_list_kwargs.append({"id": stripe_invoice.id, **def_kwarg})

        return all_list_kwargs

    @staticmethod
    def get_list_kwargs_pm(default_list_kwargs):
        """Returns sequence of kwargs to sync Payment Methods for
        all Stripe Accounts"""

        all_list_kwargs = []

        # Listing without a `type` returns every payment method type (except
        # `custom`), so there's no need to iterate over PaymentMethodType. This
        # also picks up types that aren't in our enum yet.
        for def_kwarg in default_list_kwargs:
            stripe_account = def_kwarg.get("stripe_account")
            api_key = def_kwarg.get("api_key")
            for stripe_customer in models.Customer.api_list(
                stripe_account=stripe_account, api_key=api_key
            ):
                all_list_kwargs.append({"customer": stripe_customer.id, **def_kwarg})

        return all_list_kwargs

    @staticmethod
    def get_list_kwargs_si(default_list_kwargs):
        """Returns sequence of kwargs to sync Subscription Items for
        all Stripe Accounts"""

        all_list_kwargs = []
        for def_kwarg in default_list_kwargs:
            stripe_account = def_kwarg.get("stripe_account")
            api_key = def_kwarg.get("api_key")
            for subscription in models.Subscription.api_list(
                stripe_account=stripe_account, api_key=api_key
            ):
                all_list_kwargs.append({"subscription": subscription.id, **def_kwarg})
        return all_list_kwargs

    @staticmethod
    def get_list_kwargs_country_spec(default_list_kwargs):
        """Returns sequence of kwargs to sync Country Specs for
        all Stripe Accounts"""

        all_list_kwargs = []
        for def_kwarg in default_list_kwargs:
            all_list_kwargs.append({"limit": 50, **def_kwarg})

        return all_list_kwargs

    @staticmethod
    def get_list_kwargs_txcd(default_list_kwargs):
        """Returns sequence of kwargs to sync Tax Codes for
        all Stripe Accounts"""

        # tax codes are the same for all Stripe Accounts
        return [{}]

    @staticmethod
    def get_list_kwargs_trr(default_list_kwargs):
        """Returns sequence of kwargs to sync Transfer Reversals for
        all Stripe Accounts"""
        all_list_kwargs = []
        for def_kwarg in default_list_kwargs:
            stripe_account = def_kwarg.get("stripe_account")
            api_key = def_kwarg.get("api_key")
            for transfer in models.Transfer.api_list(
                stripe_account=stripe_account, api_key=api_key
            ):
                all_list_kwargs.append({"id": transfer.id, **def_kwarg})

        return all_list_kwargs

    @staticmethod
    def get_list_kwargs_fee_refund(default_list_kwargs):
        """Returns sequence of kwargs to sync Application Fee Refunds for
        all Stripe Accounts"""
        all_list_kwargs = []
        for def_kwarg in default_list_kwargs:
            stripe_account = def_kwarg.get("stripe_account")
            api_key = def_kwarg.get("api_key")
            for fee in models.ApplicationFee.api_list(
                stripe_account=stripe_account, api_key=api_key
            ):
                all_list_kwargs.append({"id": fee.id, **def_kwarg})

        return all_list_kwargs

    @staticmethod
    def get_list_kwargs_tax_id(default_list_kwargs):
        """Returns sequence of kwargs to sync Tax Ids for
        all Stripe Accounts"""
        all_list_kwargs = []
        for def_kwarg in default_list_kwargs:
            stripe_account = def_kwarg.get("stripe_account")
            api_key = def_kwarg.get("api_key")
            for customer in models.Customer.api_list(
                stripe_account=stripe_account, api_key=api_key
            ):
                all_list_kwargs.append({"id": customer.id, **def_kwarg})

        return all_list_kwargs

    @staticmethod
    def get_list_kwargs_sis(default_list_kwargs):
        """Returns sequence of kwargs to sync Usage Record Summarys for
        all Stripe Accounts"""
        all_list_kwargs = []
        for def_kwarg in default_list_kwargs:
            stripe_account = def_kwarg.get("stripe_account")
            api_key = def_kwarg.get("api_key")
            for subscription in models.Subscription.api_list(
                stripe_account=stripe_account, api_key=api_key
            ):
                for subscription_item in models.SubscriptionItem.api_list(
                    subscription=subscription.id,
                    stripe_account=stripe_account,
                    api_key=api_key,
                ):
                    all_list_kwargs.append({"id": subscription_item.id, **def_kwarg})

        return all_list_kwargs

    # todo handle supoorting double + nested fields like data.invoice.subscriptions.customer etc?
    def get_list_kwargs(self, model, api_key: str):
        """
        Returns a sequence of kwargs dicts to pass to model.api_list

        This allows us to sync models that require parameters to api_list

        :param model:
        :return: Sequence[dict]
        """

        list_kwarg_handlers_dict = {
            "LineItem": self.get_list_kwargs_il,
            "PaymentMethod": self.get_list_kwargs_pm,
            "SubscriptionItem": self.get_list_kwargs_si,
            "CountrySpec": self.get_list_kwargs_country_spec,
            "TransferReversal": self.get_list_kwargs_trr,
            "ApplicationFeeRefund": self.get_list_kwargs_fee_refund,
            "TaxCode": self.get_list_kwargs_txcd,
            "TaxId": self.get_list_kwargs_tax_id,
        }

        # get all Stripe Accounts for the given platform account.
        # note that we need to fetch from Stripe as we have no way of knowing that the ones in the local db are up to date
        # as this can also be the first time the user runs sync.
        accs_set = self.get_stripe_account(api_key=api_key)

        default_list_kwargs = self.get_default_list_kwargs(
            model, accs_set, api_key=api_key
        )

        handler = list_kwarg_handlers_dict.get(
            model.__name__, lambda _: default_list_kwargs
        )

        return handler(default_list_kwargs)

    def sync_bank_accounts_and_cards(self, instance, *, stripe_account, api_key):
        """
        Syncs Bank Accounts and Cards for both customers and all external accounts
        """
        type = getattr(instance, "type", None)
        kwargs = {
            "api_key": api_key,
            "stripe_account": stripe_account,
            "stripe_version": djstripe_settings.STRIPE_API_VERSION,
        }

        if type in (enums.AccountType.custom, enums.AccountType.express) and isinstance(
            instance, models.Account
        ):
            # fetch all Card and BankAccount objects associated with the instance
            items = models.Account.stripe_class.list_external_accounts(
                id=instance.id, **kwargs
            ).auto_paging_iter()

            self.start_sync(items, instance, api_key=api_key)
        elif isinstance(instance, models.Customer):
            for object in ("card", "bank_account"):
                # fetch all Card and BankAccount objects associated with the instance
                items = models.Customer.stripe_class.list_sources(
                    customer=instance.id, object=object, **kwargs
                ).auto_paging_iter()

                self.start_sync(items, instance, api_key=api_key)

    def start_sync(self, items, instance, api_key: str):
        bank_count = 0
        card_count = 0
        for item in items:
            if item.object == "bank_account":
                model = models.BankAccount
                bank_count += 1
            elif item.object == "card":
                model = models.Card
                card_count += 1

            item_obj = model.sync_from_stripe_data(item, api_key=api_key)

            self.stdout.write(
                f"\tSyncing {model._meta.verbose_name} ({instance}): id={item_obj.id},"
                f" pk={item_obj.pk}"
            )

        if bank_count + card_count > 0:
            self.stdout.write(
                f"\tSynced {bank_count} BankAccounts and {card_count} Cards"
            )
