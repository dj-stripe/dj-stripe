import logging
import uuid
from datetime import timedelta

from django.db import IntegrityError, models
from django.utils import dateformat, timezone
from django.utils.encoding import smart_text

from .. import settings as djstripe_settings
from ..fields import (
    StripeDateTimeField, StripeFieldMixin, StripeIdField,
    StripeJSONField, StripeNullBooleanField, StripeTextField
)
from ..managers import StripeObjectManager


logger = logging.getLogger(__name__)


class StripeObject(models.Model):
    # This must be defined in descendants of this model/mixin
    # e.g. Event, Charge, Customer, etc.
    stripe_class = None
    expand_fields = []
    stripe_dashboard_item_name = ""

    objects = models.Manager()
    stripe_objects = StripeObjectManager()

    djstripe_id = models.BigAutoField(
        verbose_name="ID", serialize=False, primary_key=True
    )

    id = StripeIdField(unique=True)
    livemode = StripeNullBooleanField(
        default=None,
        null=True,
        stripe_required=False,
        help_text="Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, "
        "this field indicates whether this record comes from Stripe test mode or live mode operation.",
    )
    created = StripeDateTimeField(
        null=True,
        stripe_required=False,
        help_text="The datetime this object was created in stripe.",
    )
    metadata = StripeJSONField(
        stripe_required=False,
        help_text="A set of key/value pairs that you can attach to an object. It can be useful for storing additional "
        "information about an object in a structured format.",
    )
    description = StripeTextField(
        stripe_required=False, help_text="A description of this object."
    )

    djstripe_created = models.DateTimeField(auto_now_add=True, editable=False)
    djstripe_updated = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True
        get_latest_by = "created"

    def get_stripe_dashboard_url(self):
        """Get the stripe dashboard url for this object."""
        base_url = "https://dashboard.stripe.com/"

        if not self.livemode:
            base_url += "test/"

        if not self.stripe_dashboard_item_name or not self.id:
            return ""
        else:
            return "{base_url}{item}/{id}".format(
                base_url=base_url,
                item=self.stripe_dashboard_item_name,
                id=self.id,
            )

    @property
    def default_api_key(self):
        return djstripe_settings.get_default_api_key(self.livemode)

    def api_retrieve(self, api_key=None):
        """
        Call the stripe API's retrieve operation for this model.

        :param api_key: The api key to use for this request. Defaults to settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """
        api_key = api_key or self.default_api_key

        return self.stripe_class.retrieve(
            id=self.id, api_key=api_key, expand=self.expand_fields
        )

    @classmethod
    def api_list(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        """
        Call the stripe API's list operation for this model.

        :param api_key: The api key to use for this request. Defualts to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string

        See Stripe documentation for accepted kwargs for each object.

        :returns: an iterator over all items in the query
        """

        return cls.stripe_class.list(api_key=api_key, **kwargs).auto_paging_iter()

    @classmethod
    def _api_create(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        """
        Call the stripe API's create operation for this model.

        :param api_key: The api key to use for this request. Defualts to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """

        return cls.stripe_class.create(api_key=api_key, **kwargs)

    def _api_delete(self, api_key=None, **kwargs):
        """
        Call the stripe API's delete operation for this model

        :param api_key: The api key to use for this request. Defualts to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """
        api_key = api_key or self.default_api_key

        return self.api_retrieve(api_key=api_key).delete(**kwargs)

    def str_parts(self):
        """
        Extend this to add information to the string representation of the object

        :rtype: list of str
        """
        return ["id={id}".format(id=self.id)]

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        """
        Gets called by this object's stripe object conversion method just before conversion.
        Use this to populate custom fields in a StripeObject from stripe data.
        """
        return data

    @classmethod
    def _stripe_object_to_record(cls, data):
        """
        This takes an object, as it is formatted in Stripe's current API for our object
        type. In return, it provides a dict. The dict can be used to create a record or
        to update a record

        This function takes care of mapping from one field name to another, converting
        from cents to dollars, converting timestamps, and eliminating unused fields
        (so that an objects.create() call would not fail).

        :param data: the object, as sent by Stripe. Parsed from JSON, into a dict
        :type data: dict
        :return: All the members from the input, translated, mutated, etc
        :rtype: dict
        """

        manipulated_data = cls._manipulate_stripe_object_hook(data)

        result = dict()
        # Iterate over all the fields that we know are related to Stripe, let each field work its own magic
        for field in filter(
            lambda x: isinstance(x, StripeFieldMixin), cls._meta.fields
        ):
            result[field.name] = field.stripe_to_db(manipulated_data)

        return result

    def _attach_objects_hook(self, cls, data):
        """
        Gets called by this object's create and sync methods just before save.
        Use this to populate fields before the model is saved.

        :param cls: The target class for the instantiated object.
        :param data: The data dictionary received from the Stripe API.
        :type data: dict
        """

        pass

    def _attach_objects_post_save_hook(self, cls, data):
        """
        Gets called by this object's create and sync methods just after save.
        Use this to populate fields after the model is saved.

        :param cls: The target class for the instantiated object.
        :param data: The data dictionary received from the Stripe API.
        :type data: dict
        """

        pass

    @classmethod
    def _create_from_stripe_object(cls, data, save=True):
        """
        Instantiates a model instance using the provided data object received
        from Stripe, and saves it to the database if specified.

        :param data: The data dictionary received from the Stripe API.
        :type data: dict
        :param save: If True, the object is saved after instantiation.
        :type save: bool
        :returns: The instantiated object.
        """

        instance = cls(**cls._stripe_object_to_record(data))
        instance._attach_objects_hook(cls, data)

        if save:
            instance.save(force_insert=True)

        instance._attach_objects_post_save_hook(cls, data)

        return instance

    @classmethod
    def _get_or_create_from_stripe_object(
        cls, data, field_name="id", refetch=True, save=True
    ):
        field = data.get(field_name)
        is_nested_data = field_name != "id"
        should_expand = False

        if isinstance(field, str):
            # A field like {"subscription": "sub_6lsC8pt7IcFpjA", ...}
            id = field
            # We'll have to expand if the field is not "id" (= is nested)
            should_expand = is_nested_data
        elif field:
            # A field like {"subscription": {"id": sub_6lsC8pt7IcFpjA", ...}}
            data = field
            id = field.get("id")
        else:
            # An empty field - We need to return nothing here because there is
            # no way of knowing what needs to be fetched!
            return None, False

        try:
            return cls.stripe_objects.get(id=id), False
        except cls.DoesNotExist:
            if is_nested_data and refetch:
                # This is what `data` usually looks like:
                # {"id": "cus_XXXX", "default_source": "card_XXXX"}
                # Leaving the default field_name ("id") will get_or_create the customer.
                # If field_name="default_source", we get_or_create the card instead.
                cls_instance = cls(id=id)
                data = cls_instance.api_retrieve()
                should_expand = False

        # The next thing to happen will be the "create from stripe object" call.
        # At this point, if we don't have data to start with (field is a str),
        # *and* we didn't refetch by id, then `should_expand` is True and we
        # don't have the data to actually create the object.
        # If this happens when syncing Stripe data, it's a djstripe bug. Report it!
        assert not should_expand, "No data to create {} from {}".format(
            cls.__name__, field_name
        )

        try:
            return cls._create_from_stripe_object(data, save=save), True
        except IntegrityError:
            return cls.stripe_objects.get(id=id), False

    @classmethod
    def _stripe_object_to_customer(cls, target_cls, data):
        """
        Search the given manager for the Customer matching this object's ``customer`` field.

        :param target_cls: The target class
        :type target_cls: Customer
        :param data: stripe object
        :type data: dict
        """

        if "customer" in data and data["customer"]:
            return target_cls._get_or_create_from_stripe_object(data, "customer")[0]

    @classmethod
    def _stripe_object_to_transfer(cls, target_cls, data):
        """
        Search the given manager for the Transfer matching this Charge object's ``transfer`` field.

        :param target_cls: The target class
        :type target_cls: Transfer
        :param data: stripe object
        :type data: dict
        """

        if "transfer" in data and data["transfer"]:
            return target_cls._get_or_create_from_stripe_object(data, "transfer")[0]

    @classmethod
    def _stripe_object_to_invoice(cls, target_cls, data):
        """
        Search the given manager for the Invoice matching this Charge object's ``invoice`` field.
        Note that the invoice field is required.

        :param target_cls: The target class
        :type target_cls: Invoice
        :param data: stripe object
        :type data: dict
        """

        return target_cls._get_or_create_from_stripe_object(data, "invoice")[0]

    @classmethod
    def _stripe_object_to_invoice_items(cls, target_cls, data, invoice):
        """
        Retrieves InvoiceItems for an invoice.

        If the invoice item doesn't exist already then it is created.

        If the invoice is an upcoming invoice that doesn't persist to the
        database (i.e. ephemeral) then the invoice items are also not saved.

        :param target_cls: The target class to instantiate per invoice item.
        :type target_cls: ``InvoiceItem``
        :param data: The data dictionary received from the Stripe API.
        :type data: dict
        :param invoice: The invoice object that should hold the invoice items.
        :type invoice: ``djstripe.models.Invoice``
        """

        lines = data.get("lines")
        if not lines:
            return []

        invoiceitems = []
        for line in lines.get("data", []):
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
            line.setdefault("date", int(dateformat.format(invoice.date, "U")))

            item, _ = target_cls._get_or_create_from_stripe_object(
                line, refetch=False, save=save
            )
            invoiceitems.append(item)

        return invoiceitems

    @classmethod
    def _stripe_object_to_subscription(cls, target_cls, data):
        """
        Search the given manager for the Subscription matching this object's ``subscription`` field.

        :param target_cls: The target class
        :type target_cls: Subscription
        :param data: stripe object
        :type data: dict
        """

        if "subscription" in data and data["subscription"]:
            return target_cls._get_or_create_from_stripe_object(data, "subscription")[0]

    def _sync(self, record_data):
        for attr, value in record_data.items():
            setattr(self, attr, value)

    @classmethod
    def sync_from_stripe_data(cls, data):
        """
        Syncs this object from the stripe data provided.

        :param data: stripe object
        :type data: dict
        """

        instance, created = cls._get_or_create_from_stripe_object(data)

        if not created:
            instance._sync(cls._stripe_object_to_record(data))
            instance._attach_objects_hook(cls, data)
            instance.save()
            instance._attach_objects_post_save_hook(cls, data)

        return instance

    def __str__(self):
        return smart_text("<{list}>".format(list=", ".join(self.str_parts())))


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
    def is_expired(self):
        return timezone.now() > self.created + timedelta(hours=24)
