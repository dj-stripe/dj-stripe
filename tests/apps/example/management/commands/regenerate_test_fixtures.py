import json
from copy import deepcopy
from typing import Dict, List, Set, Type

import stripe.api_resources
import stripe.stripe_object
from django.core.management import BaseCommand
from stripe.error import InvalidRequestError

import djstripe.models
import tests
from djstripe import settings as djstripe_settings
from djstripe.utils import get_id_from_stripe_data

"""
Key used to store fake ids in the real stripe object's metadata dict
"""
FAKE_ID_METADATA_KEY = "djstripe_test_fake_id"


class Command(BaseCommand):
    """
    This does the following:

    1) Load existing fixtures from JSON files
    2) Attempts to read the corresponding objects from Stripe
    3) If found, for types Stripe doesn't allow us to choose ids for,
        we build a map between the fake ids in the fixtures and real Stripe ids
    3) If not found, creates objects in Stripe from the fixtures
    4) Save objects back as fixtures, using fake ids if available

    The rationale for this is so that the fixtures can automatically be updated
    with Stripe schema changes running this command.

    This should make keeping our tests and model schema compatible with Stripe
    schema changes less pain-staking and simplify the process of upgrading
    the targeted Stripe API version.
    """

    help = "Command to update test fixtures using a real Stripe account."

    fake_data_map = {}  # type: Dict[Type[djstripe.models.StripeModel], List]
    fake_id_map = {}  # type: Dict[str, str]

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete-stale",
            action="store_true",
            help="Delete any untouched fixtures in the directory",
        )
        parser.add_argument(
            "--update-sideeffect-fields",
            action="store_true",
            help="Don't preserve sideeffect fields such as 'created'",
        )

    def handle(self, *args, **options):
        do_delete_stale_fixtures = options["delete_stale"]
        do_preserve_sideeffect_fields = not options["update_sideeffect_fields"]
        common_readonly_fields = ["object", "created", "updated", "livemode"]
        common_sideeffect_fields = ["created"]

        # TODO - is it be possible to get a list of which fields are writable from
        #  the API?  maybe using https://github.com/stripe/openapi ?
        #  (though that's only for current version)

        """
        Fields that we treat as read-only.
        Most of these will cause an error if sent to the Stripe API.
        """
        model_extra_readonly_fields = {
            djstripe.models.Account: ["id"],
            djstripe.models.Customer: [
                "account_balance",
                "currency",
                "default_source",
                "delinquent",
                "invoice_prefix",
                "subscriptions",
                "sources",
            ],
            djstripe.models.BankAccount: [
                "id",
                "bank_name",
                "customer",
                "last4",
                "fingerprint",
                "status",
            ],
            djstripe.models.Card: [
                "id",
                "address_line1_check",
                "address_zip_check",
                "brand",
                "country",
                "customer",
                "cvc_check",
                "dynamic_last4",
                "exp_month",
                "exp_year",
                "fingerprint",
                "funding",
                "last4",
                "tokenization_method",
            ],
            djstripe.models.PaymentIntent: ["id"],
            djstripe.models.PaymentMethod: ["id"],
            djstripe.models.Plan: [
                # Can only specify one of amount and amount_decimal
                "amount_decimal"
            ],
            djstripe.models.Source: [
                "id",
                "amount",
                "card",
                "client_secret",
                "currency",
                "customer",
                "flow",
                "owner",
                "statement_descriptor",
                "status",
                "type",
                "usage",
            ],
            djstripe.models.Subscription: [
                "id",
                # not actually read-only
                "billing_cycle_anchor",
                "billing",
                "current_period_end",
                "current_period_start",
                # workaround for "the
                # `invoice_customer_balance_settings[consume_applied_balance_on_void]`
                # parameter is only supported in API version 2019-11-05 and below.
                # See
                # https://stripe.com/docs/api#versioning and
                # https://stripe.com/docs/upgrades#2019-12-03 for more detail.
                "invoice_customer_balance_settings",
                "latest_invoice",
                "start",
                "start_date",
                "status",
            ],
            djstripe.models.TaxRate: ["id"],
        }  # type: Dict[Type[djstripe.models.StripeModel], List[str]]

        """
        Fields that we don't care about the value of, and that preserving
        allows us to avoid churn in the fixtures
        """
        model_sideeffect_fields = {
            djstripe.models.BalanceTransaction: ["available_on"],
            djstripe.models.Source: ["client_secret"],
            djstripe.models.Charge: ["receipt_url"],
            djstripe.models.Subscription: [
                "billing_cycle_anchor",
                "current_period_start",
                "current_period_end",
                "start",
                "start_date",
            ],
            djstripe.models.SubscriptionItem: [
                # we don't currently track separate fixtures for SubscriptionItems
                "id"
            ],
            djstripe.models.Product: ["updated"],
            djstripe.models.Invoice: [
                "date",
                "finalized_at",
                "hosted_invoice_url",
                "invoice_pdf",
                "webhooks_delivered_at",
                "period_start",
                "period_end",
                # we don't currently track separate fixtures for SubscriptionItems
                "subscription_item",
            ],
        }  # type: Dict[Type[djstripe.models.StripeModel], List[str]]

        object_sideeffect_fields = {
            model.stripe_class.OBJECT_NAME: set(v)
            for model, v in model_sideeffect_fields.items()
        }  # type: Dict[str, Set[str]]

        self.fake_data_map = {
            # djstripe.models.Account: [tests.FAKE_ACCOUNT],
            djstripe.models.Customer: [
                tests.FAKE_CUSTOMER,
                tests.FAKE_CUSTOMER_II,
                tests.FAKE_CUSTOMER_III,
                tests.FAKE_CUSTOMER_IV,
            ],
            djstripe.models.BankAccount: [tests.FAKE_BANK_ACCOUNT_SOURCE],
            djstripe.models.Card: [
                tests.FAKE_CARD,
                tests.FAKE_CARD_II,
                tests.FAKE_CARD_III,
            ],
            djstripe.models.Source: [tests.FAKE_SOURCE],
            djstripe.models.Plan: [tests.FAKE_PLAN, tests.FAKE_PLAN_II],
            djstripe.models.Price: [tests.FAKE_PRICE, tests.FAKE_PRICE_II],
            djstripe.models.Product: [tests.FAKE_PRODUCT],
            djstripe.models.TaxRate: [
                tests.FAKE_TAX_RATE_EXAMPLE_1_VAT,
                tests.FAKE_TAX_RATE_EXAMPLE_2_SALES,
            ],
            djstripe.models.Subscription: [
                tests.FAKE_SUBSCRIPTION,
                tests.FAKE_SUBSCRIPTION_II,
                tests.FAKE_SUBSCRIPTION_III,
                tests.FAKE_SUBSCRIPTION_MULTI_PLAN,
            ],
            djstripe.models.SubscriptionSchedule: [
                tests.FAKE_SUBSCRIPTION_SCHEDULE,
            ],
            djstripe.models.Invoice: [tests.FAKE_INVOICE, tests.FAKE_INVOICE_IV],
            djstripe.models.Charge: [tests.FAKE_CHARGE],
            djstripe.models.PaymentIntent: [tests.FAKE_PAYMENT_INTENT_I],
            djstripe.models.PaymentMethod: [
                tests.FAKE_PAYMENT_METHOD_I,
                tests.FAKE_CARD_AS_PAYMENT_METHOD,
            ],
            djstripe.models.BalanceTransaction: [tests.FAKE_BALANCE_TRANSACTION],
        }

        self.init_fake_id_map()

        objs = []

        # Regenerate each of the fixture objects via Stripe
        # We re-fetch objects in a second pass if they were created during
        # the first pass, to ensure nested objects are up to date
        # (eg Customer.subscriptions),
        for n in range(2):
            any_created = False
            self.stdout.write(f"Updating fixture objects, pass {n}")

            # reset the objects list since we don't want to keep those from
            # the first pass
            objs.clear()

            for model_class, old_objs in self.fake_data_map.items():
                readonly_fields = (
                    common_readonly_fields
                    + model_extra_readonly_fields.get(model_class, [])
                )

                for old_obj in old_objs:
                    created, obj = self.update_fixture_obj(
                        old_obj=deepcopy(old_obj),
                        model_class=model_class,
                        readonly_fields=readonly_fields,
                        do_preserve_sideeffect_fields=do_preserve_sideeffect_fields,
                        object_sideeffect_fields=object_sideeffect_fields,
                        common_sideeffect_fields=common_sideeffect_fields,
                    )

                    objs.append(obj)
                    any_created = created or any_created

            if not any_created:
                # nothing created on this pass, no need to continue
                break
        else:
            self.stderr.write(
                "Warning, unexpected behaviour - some fixtures still being created "
                "in second pass?"
            )

        # Now the fake_id_map should be complete and the objs should be up to date,
        # save all the fixtures
        paths = set()
        for obj in objs:
            path = self.save_fixture(obj)
            paths.add(path)

        if do_delete_stale_fixtures:
            for path in tests.FIXTURE_DIR_PATH.glob("*.json"):
                if path in paths:
                    continue
                else:
                    self.stdout.write("deleting {}".format(path))
                    path.unlink()

    def init_fake_id_map(self):
        """
        Build a mapping between fake ids stored in Stripe metadata and those obj's
        actual ids

        We do this so we can have fixtures with stable ids for objects Stripe doesn't
        allow us to specify an id for (eg Card).

        Fixtures and tests will use the fake ids, when we talk to stripe we use the
        real ids
        :return:
        """

        for fake_customer in self.fake_data_map[djstripe.models.Customer]:
            try:
                # can only access Cards via the customer
                customer = djstripe.models.Customer(
                    id=fake_customer["id"]
                ).api_retrieve()
            except InvalidRequestError:
                self.stdout.write(
                    f"Fake customer {fake_customer['id']} doesn't exist in Stripe yet"
                )
                return

            # assume that test customers don't have more than 100 cards...
            for card in customer.sources.list(limit=100):
                self.update_fake_id_map(card)

            for payment_method in djstripe.models.PaymentMethod.api_list(
                customer=customer.id, type="card"
            ):
                self.update_fake_id_map(payment_method)

            for subscription in customer["subscriptions"]["data"]:
                self.update_fake_id_map(subscription)

        for tax_rate in djstripe.models.TaxRate.api_list():
            self.update_fake_id_map(tax_rate)

    def update_fake_id_map(self, obj):
        fake_id = self.get_fake_id(obj)
        actual_id = obj["id"]

        if fake_id:
            if fake_id in self.fake_id_map:
                assert self.fake_id_map[fake_id] == actual_id, (
                    f"Duplicate fake_id {fake_id} - reset your test Stripe data at "
                    f"https://dashboard.stripe.com/account/data"
                )

            self.fake_id_map[fake_id] = actual_id

            return fake_id
        else:
            return actual_id

    def get_fake_id(self, obj):
        """
        Get a stable fake id from a real Stripe object, we use this so that fixtures
         are stable
        :param obj:
        :return:
        """
        fake_id = None

        if isinstance(obj, str):
            real_id = obj
            real_id_map = {v: k for k, v in self.fake_id_map.items()}

            fake_id = real_id_map.get(real_id)
        elif "metadata" in obj:
            # Note: not all objects have a metadata dict
            # (eg Account, BalanceTransaction don't)
            fake_id = obj.get("metadata", {}).get(FAKE_ID_METADATA_KEY)
        elif obj.get("object") == "balance_transaction":
            # assume for purposes of fixture generation that 1 balance_transaction per
            # source charge (etc)
            fake_source_id = self.get_fake_id(obj["source"])

            fake_id = "txn_fake_{}".format(fake_source_id)

        return fake_id

    def fake_json_ids(self, json_str):
        """
        Replace real ids with fakes ones in the JSON fixture

        Do this on the serialized JSON string since it's a simple string replace
        :param json_str:
        :return:
        """
        for fake_id, actual_id in self.fake_id_map.items():
            json_str = json_str.replace(actual_id, fake_id)

        return json_str

    def unfake_json_ids(self, json_str):
        """
        Replace fake ids with actual ones in the JSON fixture

        Do this on the serialized JSON string since it's a simple string replace
        :param json_str:
        :return:
        """
        for fake_id, actual_id in self.fake_id_map.items():
            json_str = json_str.replace(fake_id, actual_id)

            # special-case: undo the replace for the djstripe_test_fake_id in metadata
            json_str = json_str.replace(
                f'"{FAKE_ID_METADATA_KEY}": "{actual_id}"',
                f'"{FAKE_ID_METADATA_KEY}": "{fake_id}"',
            )

        return json_str

    def update_fixture_obj(
        self,
        old_obj,
        model_class,
        readonly_fields,
        do_preserve_sideeffect_fields,
        object_sideeffect_fields,
        common_sideeffect_fields,
    ):
        """
        Given a fixture object, update it via stripe
        :param model_class:
        :param old_obj:
        :param readonly_fields:
        :return:
        """

        # restore real ids from Stripe
        old_obj = json.loads(self.unfake_json_ids(json.dumps(old_obj)))

        id_ = old_obj["id"]

        self.stdout.write(f"{model_class.__name__} {id_}", ending="")

        # For objects that we can't directly choose the ids of
        # (and that will thus vary between stripe accounts)
        # we fetch the id from a related object
        if issubclass(model_class, djstripe.models.Account):
            created, obj = self.get_or_create_stripe_account(
                old_obj=old_obj, readonly_fields=readonly_fields
            )
        elif issubclass(model_class, djstripe.models.BankAccount):
            created, obj = self.get_or_create_stripe_bank_account(
                old_obj=old_obj, readonly_fields=readonly_fields
            )
        elif issubclass(model_class, djstripe.models.Card):
            created, obj = self.get_or_create_stripe_card(
                old_obj=old_obj, readonly_fields=readonly_fields
            )
        elif issubclass(model_class, djstripe.models.Source):
            created, obj = self.get_or_create_stripe_source(
                old_obj=old_obj, readonly_fields=readonly_fields
            )
        elif issubclass(model_class, djstripe.models.Invoice):
            created, obj = self.get_or_create_stripe_invoice(
                old_obj=old_obj, writable_fields=["metadata"]
            )
        elif issubclass(model_class, djstripe.models.Charge):
            created, obj = self.get_or_create_stripe_charge(
                old_obj=old_obj, writable_fields=["metadata"]
            )
        elif issubclass(model_class, djstripe.models.PaymentIntent):
            created, obj = self.get_or_create_stripe_payment_intent(
                old_obj=old_obj, writable_fields=["metadata"]
            )
        elif issubclass(model_class, djstripe.models.PaymentMethod):
            created, obj = self.get_or_create_stripe_payment_method(
                old_obj=old_obj, writable_fields=["metadata"]
            )
        elif issubclass(model_class, djstripe.models.BalanceTransaction):
            created, obj = self.get_or_create_stripe_balance_transaction(
                old_obj=old_obj
            )
        else:
            try:
                # fetch from Stripe, using the active API version
                # this allows us regenerate the fixtures from Stripe
                # and hopefully, automatically get schema changes
                obj = model_class(id=id_).api_retrieve()
                created = False

                self.stdout.write("    found")
            except InvalidRequestError:
                self.stdout.write("    creating")

                create_obj = deepcopy(old_obj)

                # create in Stripe
                for k in readonly_fields:
                    create_obj.pop(k, None)

                if issubclass(model_class, djstripe.models.Subscription):
                    create_obj = self.pre_process_subscription(create_obj=create_obj)

                obj = model_class._api_create(**create_obj)
                created = True

        self.update_fake_id_map(obj)

        if do_preserve_sideeffect_fields:
            obj = self.preserve_old_sideeffect_values(
                old_obj=old_obj,
                new_obj=obj,
                object_sideeffect_fields=object_sideeffect_fields,
                common_sideeffect_fields=common_sideeffect_fields,
            )

        return created, obj

    def get_or_create_stripe_account(self, old_obj, readonly_fields):
        obj = djstripe.models.Account().api_retrieve()

        return True, obj

    def get_or_create_stripe_bank_account(self, old_obj, readonly_fields):
        customer_id = old_obj["customer"]

        try:
            obj = stripe.Customer.retrieve_source(customer_id, old_obj["id"])
            created = False

            self.stdout.write("    found")
        except InvalidRequestError:
            self.stdout.write("    creating")

            create_obj = deepcopy(old_obj)

            # create in Stripe
            for k in readonly_fields:
                create_obj.pop(k, None)

            # see https://stripe.com/docs/connect/testing#account-numbers
            # we've stash the account number in the metadata
            # so we can regenerate the fixture
            create_obj["account_number"] = old_obj["metadata"][
                "djstripe_test_fixture_account_number"
            ]
            create_obj["object"] = "bank_account"

            obj = stripe.Customer.create_source(customer_id, source=create_obj)

            created = True

        return created, obj

    def get_or_create_stripe_card(self, old_obj, readonly_fields):
        customer_id = old_obj["customer"]

        try:
            obj = stripe.Customer.retrieve_source(customer_id, old_obj["id"])
            created = False

            self.stdout.write("    found")
        except InvalidRequestError:
            self.stdout.write("    creating")

            create_obj = deepcopy(old_obj)

            # create in Stripe
            for k in readonly_fields:
                create_obj.pop(k, None)

            obj = stripe.Customer.create_source(**{"source": "tok_visa"})

            for k, v in create_obj.items():
                setattr(obj, k, v)

            obj.save()
            created = True

        return created, obj

    def get_or_create_stripe_source(self, old_obj, readonly_fields):
        customer_id = old_obj["customer"]

        try:
            obj = stripe.Customer.retrieve_source(customer_id, old_obj["id"])
            created = False

            self.stdout.write("    found")
        except InvalidRequestError:
            self.stdout.write("    creating")

            create_obj = deepcopy(old_obj)

            # create in Stripe
            for k in readonly_fields:
                create_obj.pop(k, None)

            source_obj = djstripe.models.Source._api_create(
                **{"token": "tok_visa", "type": "card"}
            )

            obj = stripe.Customer.create_source(**{"source": source_obj.id})

            for k, v in create_obj.items():
                setattr(obj, k, v)

            obj.save()
            created = True

        return created, obj

    def get_or_create_stripe_invoice(self, old_obj, writable_fields):
        subscription = djstripe.models.Subscription(
            id=old_obj["subscription"]
        ).api_retrieve()
        id_ = subscription["latest_invoice"]

        try:
            obj = djstripe.models.Invoice(id=id_).api_retrieve()
            created = False

            self.stdout.write(f"    found {id_}")
        except InvalidRequestError:
            assert False, "Expected to find invoice via subscription"

        for k in writable_fields:
            if isinstance(obj.get(k), dict):
                # merge dicts (eg metadata)
                obj[k].update(old_obj.get(k, {}))
            else:
                obj[k] = old_obj[k]

        obj.save()

        return created, obj

    def get_or_create_stripe_charge(self, old_obj, writable_fields):
        invoice = djstripe.models.Invoice(id=old_obj["invoice"]).api_retrieve()
        id_ = invoice["charge"]

        try:
            obj = djstripe.models.Charge(id=id_).api_retrieve()
            created = False

            self.stdout.write(f"    found {id_}")
        except InvalidRequestError:
            assert False, "Expected to find charge via invoice"

        for k in writable_fields:
            if isinstance(obj.get(k), dict):
                # merge dicts (eg metadata)
                obj[k].update(old_obj.get(k, {}))
            else:
                obj[k] = old_obj[k]

        obj.save()

        return created, obj

    def get_or_create_stripe_payment_intent(self, old_obj, writable_fields):
        invoice = djstripe.models.Invoice(id=old_obj["invoice"]).api_retrieve()
        id_ = invoice["payment_intent"]

        try:
            obj = djstripe.models.PaymentIntent(id=id_).api_retrieve()
            created = False

            self.stdout.write(f"    found {id_}")
        except InvalidRequestError:
            assert False, "Expected to find payment_intent via invoice"

        for k in writable_fields:
            if isinstance(obj.get(k), dict):
                # merge dicts (eg metadata)
                obj[k].update(old_obj.get(k, {}))
            else:
                obj[k] = old_obj[k]

        obj.save()

        return created, obj

    def get_or_create_stripe_payment_method(self, old_obj, writable_fields):
        id_ = old_obj["id"]
        customer_id = old_obj["customer"]
        type_ = old_obj["type"]

        try:
            obj = djstripe.models.PaymentMethod(id=id_).api_retrieve()
            created = False

            self.stdout.write("    found")
        except InvalidRequestError:
            self.stdout.write("    creating")

            obj = djstripe.models.PaymentMethod()._api_create(
                type=type_, card={"token": "tok_visa"}
            )

            stripe.PaymentMethod.attach(
                obj["id"],
                customer=customer_id,
                api_key=djstripe_settings.djstripe_settings.STRIPE_SECRET_KEY,
            )

            for k in writable_fields:
                if isinstance(obj.get(k), dict):
                    # merge dicts (eg metadata)
                    obj[k].update(old_obj.get(k, {}))
                else:
                    obj[k] = old_obj[k]

            obj.save()

            created = True

        return created, obj

    def get_or_create_stripe_balance_transaction(self, old_obj):
        source = old_obj["source"]

        if source.startswith("ch_"):
            charge = djstripe.models.Charge(id=source).api_retrieve()
            id_ = get_id_from_stripe_data(charge["balance_transaction"])

        try:
            obj = djstripe.models.BalanceTransaction(id=id_).api_retrieve()
            created = False

            self.stdout.write(f"    found {id_}")
        except InvalidRequestError:
            assert False, "Expected to find balance transaction via source"

        return created, obj

    def save_fixture(self, obj):
        type_name = obj["object"]
        id_ = self.update_fake_id_map(obj)

        fixture_path = tests.FIXTURE_DIR_PATH.joinpath(f"{type_name}_{id_}.json")

        with fixture_path.open("w") as f:
            json_str = self.fake_json_ids(json.dumps(obj, indent=4))

            f.write(json_str)

        return fixture_path

    def pre_process_subscription(self, create_obj):
        # flatten plan/items/tax rates on create

        items = create_obj.get("items", {}).get("data", [])

        if len(items):
            # don't try and create with both plan and item (list of plans)
            create_obj.pop("plan", None)
            create_obj.pop("quantity", None)

            # TODO - move this to SubscriptionItem handling?
            subscription_item_create_fields = {
                "plan",
                "billing_thresholds",
                "metadata",
                "quantity",
                "tax_rates",
            }
            create_items = []

            for item in items:
                create_item = {
                    k: v
                    for k, v in item.items()
                    if k in subscription_item_create_fields
                }

                create_item["plan"] = get_id_from_stripe_data(create_item["plan"])

                if create_item.get("tax_rates", []):
                    create_item["tax_rates"] = [
                        get_id_from_stripe_data(t) for t in create_item["tax_rates"]
                    ]

                create_items.append(create_item)

            create_obj["items"] = create_items
        else:
            # don't try and send empty items list
            create_obj.pop("items", None)
            create_obj["plan"] = get_id_from_stripe_data(create_obj["plan"])

        if create_obj.get("default_tax_rates", []):
            create_obj["default_tax_rates"] = [
                get_id_from_stripe_data(t) for t in create_obj["default_tax_rates"]
            ]

            # don't send both default_tax_rates and tax_percent
            create_obj.pop("tax_percent", None)

        return create_obj

    def preserve_old_sideeffect_values(
        self, old_obj, new_obj, object_sideeffect_fields, common_sideeffect_fields
    ):
        """
        Try to preserve values of side-effect fields from old_obj,
        to reduce churn in fixtures
        """
        object_name = new_obj.get("object")
        sideeffect_fields = object_sideeffect_fields.get(object_name, set()).union(
            set(common_sideeffect_fields)
        )

        old_obj = old_obj or {}

        for f, old_val in old_obj.items():
            try:
                new_val = new_obj[f]
            except KeyError:
                continue

            if isinstance(new_val, stripe.api_resources.ListObject):
                # recursively process nested lists
                for n, (old_val_item, new_val_item) in enumerate(
                    zip(old_val.get("data", []), new_val.data)
                ):
                    new_val.data[n] = self.preserve_old_sideeffect_values(
                        old_obj=old_val_item,
                        new_obj=new_val_item,
                        object_sideeffect_fields=object_sideeffect_fields,
                        common_sideeffect_fields=common_sideeffect_fields,
                    )
            elif isinstance(new_val, stripe.stripe_object.StripeObject):
                # recursively process nested objects
                new_obj[f] = self.preserve_old_sideeffect_values(
                    old_obj=old_val,
                    new_obj=new_val,
                    object_sideeffect_fields=object_sideeffect_fields,
                    common_sideeffect_fields=common_sideeffect_fields,
                )
            elif (
                f in sideeffect_fields
                and type(old_val) == type(new_val)
                and old_val != new_val
            ):
                # only preserve old values if the type is the same
                new_obj[f] = old_val

        return new_obj
