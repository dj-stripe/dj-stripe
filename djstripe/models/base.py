import logging
import uuid
from datetime import timedelta
from typing import Dict, List, Optional, Type

from django.apps import apps
from django.db import IntegrityError, models, transaction
from django.utils import dateformat, timezone
from stripe.api_resources.abstract.api_resource import APIResource
from stripe.error import InvalidRequestError
from stripe.util import convert_to_stripe_object

from ..exceptions import ImpossibleAPIRequest
from ..fields import (
    JSONField,
    StripeDateTimeField,
    StripeForeignKey,
    StripeIdField,
    StripePercentField,
)
from ..managers import StripeModelManager
from ..settings import djstripe_settings
from ..utils import get_friendly_currency_amount, get_id_from_stripe_data

logger = logging.getLogger(__name__)


class StripeBaseModel(models.Model):
    stripe_class: Type[APIResource] = APIResource

    djstripe_created = models.DateTimeField(auto_now_add=True, editable=False)
    djstripe_updated = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True

    @classmethod
    def api_list(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        """
        Call the stripe API's list operation for this model.

        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string

        See Stripe documentation for accepted kwargs for each object.

        :returns: an iterator over all items in the query
        """

        return cls.stripe_class.list(api_key=api_key, **kwargs).auto_paging_iter()


class StripeModel(StripeBaseModel):
    # This must be defined in descendants of this model/mixin
    # e.g. Event, Charge, Customer, etc.
    expand_fields: List[str] = []
    stripe_dashboard_item_name = ""

    objects = models.Manager()
    stripe_objects = StripeModelManager()

    djstripe_id = models.BigAutoField(
        verbose_name="ID", serialize=False, primary_key=True
    )
    id = StripeIdField(unique=True)

    djstripe_owner_account: Optional[StripeForeignKey] = StripeForeignKey(
        "djstripe.Account",
        on_delete=models.CASCADE,
        to_field="id",
        null=True,
        blank=True,
        help_text="The Stripe Account this object belongs to.",
    )

    livemode = models.BooleanField(
        null=True,
        default=None,
        blank=True,
        help_text="Null here indicates that the livemode status is unknown or was "
        "previously unrecorded. Otherwise, this field indicates whether this record "
        "comes from Stripe test mode or live mode operation.",
    )
    created = StripeDateTimeField(
        null=True,
        blank=True,
        help_text="The datetime this object was created in stripe.",
    )
    metadata = JSONField(
        null=True,
        blank=True,
        help_text="A set of key/value pairs that you can attach to an object. "
        "It can be useful for storing additional information about an object in "
        "a structured format.",
    )
    description = models.TextField(
        null=True, blank=True, help_text="A description of this object."
    )

    class Meta(StripeBaseModel.Meta):
        abstract = True
        get_latest_by = "created"

    def _get_base_stripe_dashboard_url(self):
        owner_path_prefix = (
            (self.djstripe_owner_account.id + "/")
            if self.djstripe_owner_account
            else ""
        )
        return "https://dashboard.stripe.com/{}{}".format(
            owner_path_prefix, "test/" if not self.livemode else ""
        )

    def get_stripe_dashboard_url(self) -> str:
        """Get the stripe dashboard url for this object."""
        if not self.stripe_dashboard_item_name or not self.id:
            return ""
        else:
            return "{base_url}{item}/{id}".format(
                base_url=self._get_base_stripe_dashboard_url(),
                item=self.stripe_dashboard_item_name,
                id=self.id,
            )

    @property
    def default_api_key(self) -> str:
        # If the class is abstract (StripeModel), fall back to default key.
        if not self._meta.abstract:
            if self.djstripe_owner_account:
                return self.djstripe_owner_account.get_default_api_key(self.livemode)
        return djstripe_settings.get_default_api_key(self.livemode)

    def _get_stripe_account_id(self, api_key=None) -> Optional[str]:
        """
        Call the stripe API's retrieve operation for this model.

        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        """
        api_key = api_key or self.default_api_key

        try:
            djstripe_owner_account = self.djstripe_owner_account
            if djstripe_owner_account is not None:
                return djstripe_owner_account.id
        except (AttributeError, KeyError, ValueError):
            pass

        # Get reverse foreign key relations to Account in case we need to
        # retrieve ourselves using that Account ID.
        reverse_account_relations = (
            field
            for field in self._meta.get_fields(include_parents=True)
            if field.is_relation and field.one_to_many
            # Avoid circular import problems by using the app registry to
            # get the model class rather than a direct import.
            and field.related_model
            is apps.get_model(app_label="djstripe", model_name="account")
        )

        # Handle case where we have a reverse relation to Account and should pass
        # that account ID to the retrieve call.
        for field in reverse_account_relations:
            # Grab the related object, using the first one we find.
            reverse_lookup_attr = field.get_accessor_name()
            account = getattr(self, reverse_lookup_attr).first()

            if account is not None:
                return account.id

        return None

    def api_retrieve(self, api_key=None, stripe_account=None):
        """
        Call the stripe API's retrieve operation for this model.

        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        """
        # Prefer passed in stripe_account if set.
        if not stripe_account:
            stripe_account = self._get_stripe_account_id(api_key)

        return self.stripe_class.retrieve(
            id=self.id,
            api_key=api_key or self.default_api_key,
            expand=self.expand_fields,
            stripe_account=stripe_account,
        )

    @classmethod
    def _api_create(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        """
        Call the stripe API's create operation for this model.

        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """

        return cls.stripe_class.create(api_key=api_key, **kwargs)

    def _api_delete(self, api_key=None, stripe_account=None, **kwargs):
        """
        Call the stripe API's delete operation for this model

        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        """
        api_key = api_key or self.default_api_key
        # Prefer passed in stripe_account if set.
        if not stripe_account:
            stripe_account = self._get_stripe_account_id(api_key)

        return self.stripe_class.delete(
            self.id, api_key=api_key, stripe_account=stripe_account, **kwargs
        )

    def _api_update(self, api_key=None, stripe_account=None, **kwargs):
        """
        Call the stripe API's modify operation for this model

        :param api_key: The api key to use for this request.
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        """
        api_key = api_key or self.default_api_key
        # Prefer passed in stripe_account if set.
        if not stripe_account:
            stripe_account = self._get_stripe_account_id(api_key)

        return self.stripe_class.modify(
            self.id, api_key=api_key, stripe_account=stripe_account, **kwargs
        )

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        """
        Gets called by this object's stripe object conversion method just before
        conversion.
        Use this to populate custom fields in a StripeModel from stripe data.
        """
        return data

    @classmethod
    def _find_owner_account(cls, data, api_key=djstripe_settings.STRIPE_SECRET_KEY):
        """
        Fetches the Stripe Account (djstripe_owner_account model field)
        linked to the class, cls.
        Tries to retreive using the Stripe_account if given.
        Otherwise uses the api_key.
        """
        from .account import Account

        # try to fetch by stripe_account. Also takes care of Stripe Connected Accounts
        if data:
            # case of Webhook Event Trigger
            if data.get("object") == "event":
                # if account key exists and has a not null value
                stripe_account_id = get_id_from_stripe_data(data.get("account"))
                if stripe_account_id:
                    return Account._get_or_retrieve(
                        id=stripe_account_id, api_key=api_key
                    )

            else:
                stripe_account = getattr(data, "stripe_account", None)
                stripe_account_id = get_id_from_stripe_data(stripe_account)
                if stripe_account_id:
                    return Account._get_or_retrieve(
                        id=stripe_account_id, api_key=api_key
                    )

        # try to fetch by the given api_key.
        return Account.get_or_retrieve_for_api_key(api_key)

    @classmethod
    def _stripe_object_to_record(
        cls,
        data: dict,
        current_ids=None,
        pending_relations: list = None,
        stripe_account: str = None,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
    ) -> Dict:
        """
        This takes an object, as it is formatted in Stripe's current API for our object
        type. In return, it provides a dict. The dict can be used to create a record or
        to update a record

        This function takes care of mapping from one field name to another, converting
        from cents to dollars, converting timestamps, and eliminating unused fields
        (so that an objects.create() call would not fail).

        :param data: the object, as sent by Stripe. Parsed from JSON, into a dict
        :param current_ids: stripe ids of objects that are currently being processed
        :type current_ids: set
        :param pending_relations: list of tuples of relations to be attached post-save
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :return: All the members from the input, translated, mutated, etc
        """
        from .webhooks import WebhookEndpoint

        manipulated_data = cls._manipulate_stripe_object_hook(data)
        if not cls.is_valid_object(manipulated_data):
            raise ValueError(
                "Trying to fit a %r into %r. Aborting."
                % (manipulated_data.get("object", ""), cls.__name__)
            )

        result = {}
        if current_ids is None:
            current_ids = set()

        # Iterate over all the fields that we know are related to Stripe,
        # let each field work its own magic
        ignore_fields = ["date_purged", "subscriber"]  # XXX: Customer hack

        # get all forward and reverse relations for given cls
        for field in cls._meta.get_fields():
            if field.name.startswith("djstripe_") or field.name in ignore_fields:
                continue

            # todo add support reverse ManyToManyField sync
            if isinstance(
                field, (models.ManyToManyRel, models.ManyToOneRel)
            ) and not isinstance(field, models.OneToOneRel):
                # We don't currently support syncing from
                # reverse side of Many relationship
                continue

            # todo for ManyToManyField one would also need to handle the case of an intermediate model being used
            # todo add support ManyToManyField sync
            if field.many_to_many:
                # We don't currently support syncing ManyToManyField
                continue

            # will work for Forward FK and OneToOneField relations and reverse OneToOneField relations
            if isinstance(field, (models.ForeignKey, models.OneToOneRel)):
                field_data, skip, is_nulled = cls._stripe_object_field_to_foreign_key(
                    field=field,
                    manipulated_data=manipulated_data,
                    current_ids=current_ids,
                    pending_relations=pending_relations,
                    stripe_account=stripe_account,
                    api_key=api_key,
                )

                if skip and not is_nulled:
                    continue
            else:
                if hasattr(field, "stripe_to_db"):
                    field_data = field.stripe_to_db(manipulated_data)
                else:
                    field_data = manipulated_data.get(field.name)

                if (
                    isinstance(field, (models.CharField, models.TextField))
                    and field_data is None
                ):
                    # do not add empty secret field for WebhookEndpoint model
                    # as stripe does not return the secret except for the CREATE call
                    if cls is WebhookEndpoint and field.name == "secret":
                        continue
                    else:
                        # TODO - this applies to StripeEnumField as well, since it
                        #  sub-classes CharField, is that intentional?
                        field_data = ""

            result[field.name] = field_data

        # For all objects other than the account object itself, get the API key
        # attached to the request, and get the matching Account for that key.
        owner_account = cls._find_owner_account(data, api_key=api_key)
        if owner_account:
            result["djstripe_owner_account"] = owner_account

        return result

    @classmethod
    def _stripe_object_field_to_foreign_key(
        cls,
        field,
        manipulated_data,
        current_ids=None,
        pending_relations=None,
        stripe_account=None,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
    ):
        """
        This converts a stripe API field to the dj stripe object it references,
        so that foreign keys can be connected up automatically.

        :param field:
        :type field: models.ForeignKey
        :param manipulated_data:
        :type manipulated_data: dict
        :param current_ids: stripe ids of objects that are currently being processed
        :type current_ids: set
        :param pending_relations: list of tuples of relations to be attached post-save
        :type pending_relations: list
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        :return:
        """
        from djstripe.models import DjstripePaymentMethod

        field_data = None
        field_name = field.name
        refetch = False
        skip = False
        # a flag to indicate if the given field is null upstream on Stripe
        is_nulled = False

        if current_ids is None:
            current_ids = set()

        if issubclass(field.related_model, StripeModel) or issubclass(
            field.related_model, DjstripePaymentMethod
        ):

            if field_name in manipulated_data:
                raw_field_data = manipulated_data.get(field_name)

                # field's value is None. Skip syncing but set as None.
                # Otherwise nulled FKs sync gets skipped.
                if not raw_field_data:
                    is_nulled = True
                    skip = True

            else:
                # field does not exist in manipulated_data dict. Skip Syncing
                skip = True
                raw_field_data = None

            id_ = get_id_from_stripe_data(raw_field_data)

            if id_ == raw_field_data:
                # A field like {"subscription": "sub_6lsC8pt7IcFpjA", ...}
                refetch = True
            else:
                # A field like {"subscription": {"id": sub_6lsC8pt7IcFpjA", ...}}
                pass

            if id_ in current_ids:
                # this object is currently being fetched, don't try to fetch again,
                # to avoid recursion instead, record the relation that should be
                # created once "object_id" object exists
                if pending_relations is not None:
                    object_id = manipulated_data["id"]
                    pending_relations.append((object_id, field, id_))
                skip = True

            # sync only if field exists and is not null
            if not skip and not is_nulled:
                # add the id of the current object to the list
                # of ids being processed.
                # This will avoid infinite recursive syncs in case a relatedmodel
                # requests the same object
                current_ids.add(id_)

                try:
                    (
                        field_data,
                        _,
                    ) = field.related_model._get_or_create_from_stripe_object(
                        manipulated_data,
                        field_name,
                        refetch=refetch,
                        current_ids=current_ids,
                        pending_relations=pending_relations,
                        stripe_account=stripe_account,
                        api_key=api_key,
                    )
                except ImpossibleAPIRequest:
                    # Found to happen in the following situation:
                    # Customer has a `default_source` set to a `card_` object,
                    # and neither the Customer nor the Card are present in db.
                    # This skip is a hack, but it will prevent a crash.
                    skip = True

                # Remove the id of the current object from the list
                # after it has been created or retrieved
                current_ids.remove(id_)

        else:
            # eg PaymentMethod, handled in hooks
            skip = True

        return field_data, skip, is_nulled

    @classmethod
    def is_valid_object(cls, data):
        """
        Returns whether the data is a valid object for the class
        """
        # .OBJECT_NAME will not exist on the base type itself
        object_name: str = getattr(cls.stripe_class, "OBJECT_NAME", "")
        if not object_name:
            return False
        return data and data.get("object") == object_name

    def _attach_objects_hook(
        self, cls, data, api_key=djstripe_settings.STRIPE_SECRET_KEY, current_ids=None
    ):
        """
        Gets called by this object's create and sync methods just before save.
        Use this to populate fields before the model is saved.

        :param cls: The target class for the instantiated object.
        :param data: The data dictionary received from the Stripe API.
        :type data: dict
        :param current_ids: stripe ids of objects that are currently being processed
        :type current_ids: set
        """

        pass

    def _attach_objects_post_save_hook(
        self,
        cls,
        data,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
        pending_relations=None,
    ):
        """
        Gets called by this object's create and sync methods just after save.
        Use this to populate fields after the model is saved.

        :param cls: The target class for the instantiated object.
        :param data: The data dictionary received from the Stripe API.
        :type data: dict
        """

        unprocessed_pending_relations = []
        if pending_relations is not None:
            for post_save_relation in pending_relations:
                object_id, field, id_ = post_save_relation

                if self.id == id_:
                    # the target instance now exists
                    target = field.model.objects.get(id=object_id)
                    setattr(target, field.name, self)
                    if isinstance(field, models.OneToOneRel):
                        # this is a reverse relationship, so the relation exists on self
                        self.save()
                    else:
                        # this is a forward relation on the target,
                        # so we need to save it
                        target.save()

                        # reload so that indirect relations back to this object
                        # eg self.charge.invoice = self are set
                        # TODO - reverse the field reference here to avoid hitting the DB?
                        self.refresh_from_db()
                else:
                    unprocessed_pending_relations.append(post_save_relation)

            if len(pending_relations) != len(unprocessed_pending_relations):
                # replace in place so passed in list is updated in calling method
                pending_relations[:] = unprocessed_pending_relations

    @classmethod
    def _create_from_stripe_object(
        cls,
        data,
        current_ids=None,
        pending_relations=None,
        save=True,
        stripe_account=None,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
    ):
        """
        Instantiates a model instance using the provided data object received
        from Stripe, and saves it to the database if specified.

        :param data: The data dictionary received from the Stripe API.
        :type data: dict
        :param current_ids: stripe ids of objects that are currently being processed
        :type current_ids: set
        :param pending_relations: list of tuples of relations to be attached post-save
        :type pending_relations: list
        :param save: If True, the object is saved after instantiation.
        :type save: bool
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        :returns: The instantiated object.
        """
        stripe_data = cls._stripe_object_to_record(
            data,
            current_ids=current_ids,
            pending_relations=pending_relations,
            stripe_account=stripe_account,
            api_key=api_key,
        )
        try:
            id_ = get_id_from_stripe_data(stripe_data)
            if id_ is not None:
                instance = cls.stripe_objects.get(id=id_)
            else:
                # Raise error on purpose to resume the _create_from_stripe_object flow
                raise cls.DoesNotExist

        except cls.DoesNotExist:
            # try to create iff instance doesn't already exist in the DB
            # TODO dictionary unpacking will not work if cls has any ManyToManyField
            instance = cls(**stripe_data)

            instance._attach_objects_hook(
                cls, data, api_key=api_key, current_ids=current_ids
            )

            if save:
                instance.save()

            instance._attach_objects_post_save_hook(
                cls, data, api_key=api_key, pending_relations=pending_relations
            )

        return instance

    @classmethod
    def _get_or_create_from_stripe_object(
        cls,
        data,
        field_name="id",
        refetch=True,
        current_ids=None,
        pending_relations=None,
        save=True,
        stripe_account=None,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
    ):
        """

        :param data:
        :param field_name:
        :param refetch:
        :param current_ids: stripe ids of objects that are currently being processed
        :type current_ids: set
        :param pending_relations: list of tuples of relations to be attached post-save
        :type pending_relations: list
        :param save:
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        :return:
        :rtype: cls, bool
        """
        field = data.get(field_name)
        is_nested_data = field_name != "id"
        should_expand = False

        if pending_relations is None:
            pending_relations = []

        id_ = get_id_from_stripe_data(field)

        if not field:
            # An empty field - We need to return nothing here because there is
            # no way of knowing what needs to be fetched!
            raise RuntimeError(
                f"dj-stripe encountered an empty field {cls.__name__}.{field_name} = {field}"
            )
        elif id_ == field:
            # A field like {"subscription": "sub_6lsC8pt7IcFpjA", ...}
            # We'll have to expand if the field is not "id" (= is nested)
            should_expand = is_nested_data
        else:
            # A field like {"subscription": {"id": sub_6lsC8pt7IcFpjA", ...}}
            data = field

        try:
            return cls.stripe_objects.get(id=id_), False
        except cls.DoesNotExist:
            if is_nested_data and refetch:
                # This is what `data` usually looks like:
                # {"id": "cus_XXXX", "default_source": "card_XXXX"}
                # Leaving the default field_name ("id") will get_or_create the customer.
                # If field_name="default_source", we get_or_create the card instead.
                cls_instance = cls(id=id_)
                try:
                    data = cls_instance.api_retrieve(
                        stripe_account=stripe_account, api_key=api_key
                    )
                except InvalidRequestError as e:
                    if "a similar object exists in" in str(e):
                        # HACK around a Stripe bug.
                        # When a File is retrieved from the Account object,
                        # a mismatch between live and test mode is possible depending
                        # on whether the file (usually the logo) was uploaded in live
                        # or test. Reported to Stripe in August 2020.
                        # Context: https://github.com/dj-stripe/dj-stripe/issues/830
                        pass
                    elif "No such PaymentMethod:" in str(e):
                        # payment methods (card_… etc) can be irretrievably deleted,
                        # but still present during sync. For example, if a refund is
                        # issued on a charge whose payment method has been deleted.
                        return None, False
                    else:
                        raise
                should_expand = False

        # The next thing to happen will be the "create from stripe object" call.
        # At this point, if we don't have data to start with (field is a str),
        # *and* we didn't refetch by id, then `should_expand` is True and we
        # don't have the data to actually create the object.
        # If this happens when syncing Stripe data, it's a djstripe bug. Report it!
        if should_expand:
            raise ValueError(f"No data to create {cls.__name__} from {field_name}")

        try:
            # We wrap the `_create_from_stripe_object` in a transaction to
            # avoid TransactionManagementError on subsequent queries in case
            # of the IntegrityError catch below. See PR #903
            with transaction.atomic():
                return (
                    cls._create_from_stripe_object(
                        data,
                        current_ids=current_ids,
                        pending_relations=pending_relations,
                        save=save,
                        stripe_account=stripe_account,
                        api_key=api_key,
                    ),
                    True,
                )
        except IntegrityError:
            # Handle the race condition that something else created the object
            # after the `get` and before `_create_from_stripe_object`.
            # This is common during webhook handling, since Stripe sends
            # multiple webhook events simultaneously,
            # each of which will cause recursive syncs. See issue #429
            return cls.stripe_objects.get(id=id_), False

    @classmethod
    def _stripe_object_to_customer(
        cls,
        target_cls,
        data,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
        current_ids=None,
    ):
        """
        Search the given manager for the Customer matching this object's
        ``customer`` field.
        :param target_cls: The target class
        :type target_cls: Customer
        :param data: stripe object
        :type data: dict
        :param current_ids: stripe ids of objects that are currently being processed
        :type current_ids: set
        """

        if "customer" in data and data["customer"]:
            return target_cls._get_or_create_from_stripe_object(
                data, "customer", current_ids=current_ids, api_key=api_key
            )[0]

    @classmethod
    def _stripe_object_to_default_tax_rates(
        cls, target_cls, data, api_key=djstripe_settings.STRIPE_SECRET_KEY
    ):
        """
        Retrieves TaxRates for a Subscription or Invoice
        :param target_cls:
        :param data:
        :param instance:
        :type instance: Union[djstripe.models.Invoice, djstripe.models.Subscription]
        :return:
        """
        tax_rates = []

        for tax_rate_data in data.get("default_tax_rates", []):
            tax_rate, _ = target_cls._get_or_create_from_stripe_object(
                tax_rate_data, refetch=False, api_key=api_key
            )
            tax_rates.append(tax_rate)

        return tax_rates

    @classmethod
    def _stripe_object_to_tax_rates(
        cls, target_cls, data, api_key=djstripe_settings.STRIPE_SECRET_KEY
    ):
        """
        Retrieves TaxRates for a SubscriptionItem or InvoiceItem
        :param target_cls:
        :param data:
        :return:
        """
        tax_rates = []

        for tax_rate_data in data.get("tax_rates", []):
            tax_rate, _ = target_cls._get_or_create_from_stripe_object(
                tax_rate_data, refetch=False, api_key=api_key
            )
            tax_rates.append(tax_rate)

        return tax_rates

    @classmethod
    def _stripe_object_set_total_tax_amounts(
        cls, target_cls, data, instance, api_key=djstripe_settings.STRIPE_SECRET_KEY
    ):
        """
        Set total tax amounts on Invoice instance
        :param target_cls:
        :param data:
        :param instance:
        :type instance: djstripe.models.Invoice
        :return:
        """
        from .billing import TaxRate

        pks = []

        for tax_amount_data in data.get("total_tax_amounts", []):
            tax_rate_data = tax_amount_data["tax_rate"]
            if isinstance(tax_rate_data, str):
                tax_rate_data = {"tax_rate": tax_rate_data}

            tax_rate, _ = TaxRate._get_or_create_from_stripe_object(
                tax_rate_data,
                field_name="tax_rate",
                refetch=True,
                api_key=api_key,
            )
            tax_amount, _ = target_cls.objects.update_or_create(
                invoice=instance,
                tax_rate=tax_rate,
                defaults={
                    "amount": tax_amount_data["amount"],
                    "inclusive": tax_amount_data["inclusive"],
                },
            )

            pks.append(tax_amount.pk)

        instance.total_tax_amounts.exclude(pk__in=pks).delete()

    @classmethod
    def _stripe_object_to_invoice_items(
        cls, target_cls, data, invoice, api_key=djstripe_settings.STRIPE_SECRET_KEY
    ):
        """
        Retrieves InvoiceItems for an invoice.

        If the invoice item doesn't exist already then it is created.

        If the invoice is an upcoming invoice that doesn't persist to the
        database (i.e. ephemeral) then the invoice items are also not saved.

        :param target_cls: The target class to instantiate per invoice item.
        :type target_cls:  Type[djstripe.models.InvoiceItem]
        :param data: The data dictionary received from the Stripe API.
        :type data: dict
        :param invoice: The invoice object that should hold the invoice items.
        :type invoice: ``djstripe.models.Invoice``
        """

        lines = data.get("lines")
        if not lines:
            return []

        invoiceitems = []
        for line in lines.auto_paging_iter():
            if invoice.id:
                save = True
                line.setdefault("invoice", invoice.id)

                if line.get("type") == "subscription":
                    # Lines for subscriptions need to be keyed based on invoice and
                    # subscription, because their id is *just* the subscription
                    # when received from Stripe. This means that future updates to
                    # a subscription will change previously saved invoices - Doing
                    # the composite key avoids this.
                    if not line["id"].startswith(invoice.id):
                        line["id"] = "{invoice_id}-{subscription_id}".format(
                            invoice_id=invoice.id, subscription_id=line["id"]
                        )
            else:
                # Don't save invoice items for ephemeral invoices
                save = False

            line.setdefault("customer", invoice.customer.id)
            line.setdefault("date", int(dateformat.format(invoice.created, "U")))

            item, _ = target_cls._get_or_create_from_stripe_object(
                line, refetch=False, save=save, api_key=api_key
            )
            invoiceitems.append(item)

        return invoiceitems

    @classmethod
    def _stripe_object_to_subscription_items(
        cls, target_cls, data, subscription, api_key=djstripe_settings.STRIPE_SECRET_KEY
    ):
        """
        Retrieves SubscriptionItems for a subscription.

        If the subscription item doesn't exist already then it is created.

        :param target_cls: The target class to instantiate per invoice item.
        :type target_cls: Type[djstripe.models.SubscriptionItem]
        :param data: The data dictionary received from the Stripe API.
        :type data: dict
        :param subscription: The subscription object that should hold the items.
        :type subscription: djstripe.models.Subscription
        """

        items = data.get("items")
        if not items:
            subscription.items.delete()
            return []

        pks = []
        subscriptionitems = []
        for item_data in items.auto_paging_iter():
            item, _ = target_cls._get_or_create_from_stripe_object(
                item_data, refetch=False, api_key=api_key
            )

            # sync the SubscriptionItem
            target_cls.sync_from_stripe_data(item_data, api_key=api_key)

            pks.append(item.pk)
            subscriptionitems.append(item)
        subscription.items.exclude(pk__in=pks).delete()

        return subscriptionitems

    @classmethod
    def _stripe_object_to_refunds(
        cls, target_cls, data, charge, api_key=djstripe_settings.STRIPE_SECRET_KEY
    ):
        """
        Retrieves Refunds for a charge
        :param target_cls: The target class to instantiate per refund
        :type target_cls: Type[djstripe.models.Refund]
        :param data: The data dictionary received from the Stripe API.
        :type data: dict
        :param charge: The charge object that refunds are for.
        :type charge: djstripe.models.Refund
        :return:
        """
        stripe_refunds = convert_to_stripe_object(data.get("refunds"))

        if not stripe_refunds:
            return []

        refund_objs = []

        for refund_data in stripe_refunds.auto_paging_iter():
            item, _ = target_cls._get_or_create_from_stripe_object(
                refund_data,
                refetch=False,
                api_key=api_key,
            )
            refund_objs.append(item)

        return refund_objs

    @classmethod
    def sync_from_stripe_data(cls, data, api_key=djstripe_settings.STRIPE_SECRET_KEY):
        """
        Syncs this object from the stripe data provided.

        Foreign keys will also be retrieved and synced recursively.

        :param data: stripe object
        :type data: dict
        :rtype: cls
        """
        current_ids = set()
        data_id = data.get("id")
        stripe_account = getattr(data, "stripe_account", None)

        if data_id:
            # stop nested objects from trying to retrieve this object before
            # initial sync is complete
            current_ids.add(data_id)

        instance, created = cls._get_or_create_from_stripe_object(
            data,
            current_ids=current_ids,
            stripe_account=stripe_account,
            api_key=api_key,
        )

        if not created:
            record_data = cls._stripe_object_to_record(
                data, api_key=api_key, stripe_account=stripe_account
            )
            for attr, value in record_data.items():
                setattr(instance, attr, value)
            instance._attach_objects_hook(
                cls, data, api_key=api_key, current_ids=current_ids
            )
            instance.save()
            instance._attach_objects_post_save_hook(cls, data, api_key=api_key)

        for field in instance._meta.concrete_fields:
            if isinstance(field, (StripePercentField, models.UUIDField)):
                # get rid of cached values
                delattr(instance, field.name)

        return instance

    @classmethod
    def _get_or_retrieve(cls, id, stripe_account=None, **kwargs):
        """
        Retrieve object from the db, if it exists. If it doesn't, query Stripe to fetch
        the object and sync with the db.
        """
        try:
            return cls.objects.get(id=id)
        except cls.DoesNotExist:
            pass

        if stripe_account:
            kwargs["stripe_account"] = str(stripe_account)

        # If no API key is specified, use the default one for the specified livemode
        # (or if no livemode is specified, the default one altogether)
        kwargs.setdefault(
            "api_key",
            djstripe_settings.get_default_api_key(livemode=kwargs.get("livemode")),
        )
        data = cls.stripe_class.retrieve(id=id, **kwargs)
        instance = cls.sync_from_stripe_data(data, api_key=kwargs.get("api_key"))
        return instance

    def __str__(self):
        return f"<id={self.id}>"


class IdempotencyKey(models.Model):
    uuid = models.UUIDField(
        max_length=36, primary_key=True, editable=False, default=uuid.uuid4
    )
    action = models.CharField(max_length=100)
    livemode = models.BooleanField(
        help_text="Whether the key was used in live or test mode."
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("action", "livemode")

    def __str__(self):
        return str(self.uuid)

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.created + timedelta(hours=24)
