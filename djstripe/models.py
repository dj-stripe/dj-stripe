# -*- coding: utf-8 -*-
"""
.. module:: djstripe.models
   :synopsis: dj-stripe - Django ORM model definitions

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

"""

from __future__ import absolute_import, division, print_function, unicode_literals

import decimal
import logging
import sys
import uuid
import warnings
from copy import deepcopy
from datetime import timedelta

import stripe
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import IntegrityError, models, transaction
from django.db.models.deletion import SET_NULL
from django.db.models.fields import BooleanField, CharField, DateTimeField, UUIDField
from django.db.models.fields.related import ForeignKey, OneToOneField
from django.utils import dateformat, six, timezone
from django.utils.encoding import python_2_unicode_compatible, smart_text
from django.utils.functional import cached_property
from six import PY3, text_type
from stripe.error import InvalidRequestError

from . import enums
from . import settings as djstripe_settings
from . import webhooks
from .context_managers import stripe_temporary_api_version
from .enums import SubscriptionStatus
from .exceptions import MultipleSubscriptionException, StripeObjectManipulationException
from .fields import (
    JSONField, PaymentMethodForeignKey, StripeBooleanField, StripeCharField, StripeCurrencyField,
    StripeDateTimeField, StripeEnumField, StripeFieldMixin, StripeIdField, StripeIntegerField,
    StripeJSONField, StripeNullBooleanField, StripePercentField, StripePositiveIntegerField, StripeTextField
)
from .managers import ChargeManager, StripeObjectManager, SubscriptionManager, TransferManager
from .signals import WEBHOOK_SIGNALS, webhook_processing_error
from .utils import QuerySetMock, get_friendly_currency_amount


logger = logging.getLogger(__name__)

# Override the default API version used by the Stripe library.
djstripe_settings.set_stripe_api_version()


class PaymentMethod(models.Model):
    """
    An internal model that abstracts the legacy Card and BankAccount
    objects with Source objects.

    Contains two fields: `id` and `type`:
    - `id` is the id of the Stripe object.
    - `type` can be `card`, `bank_account` or `source`.
    """
    id = CharField(max_length=255, primary_key=True)
    type = CharField(max_length=12, db_index=True)

    @classmethod
    def from_stripe_object(cls, data):
        source_type = data["object"]
        model = cls._model_for_type(source_type)

        with transaction.atomic():
            model.sync_from_stripe_data(data)
            instance, _ = cls.objects.get_or_create(
                id=data["id"], defaults={"type": source_type}
            )

        return instance

    @classmethod
    def _get_or_create_source(cls, data, source_type):
        try:
            model = cls._model_for_type(source_type)
            model._get_or_create_from_stripe_object(data)
        except ValueError as e:
            # This may happen if we have source types we don't know about.
            # Let's not make dj-stripe entirely unusable if that happens.
            logger.warning("Could not sync source of type %r: %s", source_type, e)

        return cls.objects.get_or_create(id=data["id"], defaults={"type": source_type})

    @classmethod
    def _model_for_type(cls, type):
        if type == "card":
            return Card
        elif type == "source":
            return Source
        elif type == "bank_account":
            return BankAccount

        raise ValueError("Unknown source type: {}".format(type))

    @property
    def stripe_id(self):
        # Deprecated (transitional)
        return self.id

    @property
    def object_model(self):
        return self._model_for_type(self.type)

    def resolve(self):
        return self.object_model.objects.get(stripe_id=self.id)


@python_2_unicode_compatible
class StripeObject(models.Model):
    # This must be defined in descendants of this model/mixin
    # e.g. Event, Charge, Customer, etc.
    stripe_class = None
    expand_fields = None
    stripe_dashboard_item_name = ""

    objects = models.Manager()
    stripe_objects = StripeObjectManager()

    djstripe_id = models.BigAutoField(verbose_name="ID", serialize=False, primary_key=True)
    stripe_id = StripeIdField(unique=True, stripe_name='id')
    livemode = StripeNullBooleanField(
        default=None,
        null=True,
        stripe_required=False,
        help_text="Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, "
        "this field indicates whether this record comes from Stripe test mode or live mode operation."
    )
    created = StripeDateTimeField(
        null=True,
        stripe_required=False,
        help_text="The datetime this object was created in stripe."
    )
    metadata = StripeJSONField(
        blank=True,
        stripe_required=False,
        help_text="A set of key/value pairs that you can attach to an object. It can be useful for storing additional "
        "information about an object in a structured format."
    )
    description = StripeTextField(blank=True, stripe_required=False, help_text="A description of this object.")

    djstripe_created = models.DateTimeField(auto_now_add=True, editable=False)
    djstripe_updated = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True

    def get_stripe_dashboard_url(self):
        """Get the stripe dashboard url for this object."""
        base_url = "https://dashboard.stripe.com/"

        if not self.livemode:
            base_url += "test/"

        if not self.stripe_dashboard_item_name or not self.stripe_id:
            return ""
        else:
            return "{base_url}{item}/{stripe_id}".format(
                base_url=base_url,
                item=self.stripe_dashboard_item_name,
                stripe_id=self.stripe_id
            )

    @property
    def default_api_key(self):
        return djstripe_settings.get_default_api_key(self.livemode)

    @property
    def id(self):
        """
        DEPRECATED(2018-01-10): Use `.djstripe_id` instead.
        """
        warnings.warn("The id field has been renamed to `djstripe_id`.", DeprecationWarning)
        return self.djstripe_id

    @property
    def stripe_timestamp(self):
        """
        DEPRECATED(2018-01-10): Use `.created` instead.
        """
        warnings.warn("The stripe_timestamp field has been renamed to `created`.", DeprecationWarning)
        return self.created

    def api_retrieve(self, api_key=None):
        """
        Call the stripe API's retrieve operation for this model.

        :param api_key: The api key to use for this request. Defaults to settings.STRIPE_SECRET_KEY.
        :type api_key: string
        """
        api_key = api_key or self.default_api_key

        return self.stripe_class.retrieve(id=self.stripe_id, api_key=api_key, expand=self.expand_fields)

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
        return ["stripe_id={id}".format(id=self.stripe_id)]

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
        for field in filter(lambda x: isinstance(x, StripeFieldMixin), cls._meta.fields):
            field_data = field.stripe_to_db(manipulated_data)
            if isinstance(field, CharField) and field_data is None:
                field_data = ""
            result[field.name] = field_data

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
    def _get_or_create_from_stripe_object(cls, data, field_name="id", refetch=True, save=True):
        field = data.get(field_name)
        is_nested_data = field_name != "id"
        should_expand = False

        if isinstance(field, six.string_types):
            # A field like {"subscription": "sub_6lsC8pt7IcFpjA", ...}
            stripe_id = field
            # We'll have to expand if the field is not "id" (= is nested)
            should_expand = is_nested_data
        elif field:
            # A field like {"subscription": {"id": sub_6lsC8pt7IcFpjA", ...}}
            data = field
            stripe_id = field.get("id")
        else:
            # An empty field - We need to return nothing here because there is
            # no way of knowing what needs to be fetched!
            return None, False

        try:
            return cls.stripe_objects.get(stripe_id=stripe_id), False
        except cls.DoesNotExist:
            if is_nested_data and refetch:
                # This is what `data` usually looks like:
                # {"id": "cus_XXXX", "default_source": "card_XXXX"}
                # Leaving the default field_name ("id") will get_or_create the customer.
                # If field_name="default_source", we get_or_create the card instead.
                cls_instance = cls(stripe_id=stripe_id)
                data = cls_instance.api_retrieve()
                should_expand = False

        # The next thing to happen will be the "create from stripe object" call.
        # At this point, if we don't have data to start with (field is a str),
        # *and* we didn't refetch by id, then `should_expand` is True and we
        # don't have the data to actually create the object.
        # If this happens when syncing Stripe data, it's a djstripe bug. Report it!
        assert not should_expand, "No data to create {} from {}".format(cls.__name__, field_name)

        try:
            return cls._create_from_stripe_object(data, save=save), True
        except IntegrityError:
            return cls.stripe_objects.get(stripe_id=stripe_id), False

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
            if invoice.stripe_id:
                save = True
                line.setdefault("invoice", invoice.stripe_id)

                if line.get("type") == "subscription":
                    # Lines for subscriptions need to be keyed based on invoice and
                    # subscription, because their id is *just* the subscription
                    # when received from Stripe. This means that future updates to
                    # a subscription will change previously saved invoices - Doing
                    # the composite key avoids this.
                    if not line["id"].startswith(invoice.stripe_id):
                        line["id"] = "{invoice_id}-{subscription_id}".format(
                            invoice_id=invoice.stripe_id,
                            subscription_id=line["id"])
            else:
                # Don't save invoice items for ephemeral invoices
                save = False

            line.setdefault("customer", invoice.customer.stripe_id)
            line.setdefault("date", int(dateformat.format(invoice.date, 'U')))

            item, _ = target_cls._get_or_create_from_stripe_object(
                line, refetch=False, save=save)
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


# ============================================================================ #
#                               Core Resources                                 #
# ============================================================================ #

# TODO: class Balance(...)

@python_2_unicode_compatible
class Charge(StripeObject):
    """
    To charge a credit or a debit card, you create a charge object. You can
    retrieve and refund individual charges as well as list all charges. Charges
    are identified by a unique random ID. (Source: https://stripe.com/docs/api/python#charges)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:

    * **object** - Unnecessary. Just check the model name.
    * **application_fee** - #. Coming soon with stripe connect functionality
    * **balance_transaction** - #
    * **order** - #
    * **refunds** - #
    * **source_transfer** - #

    .. attention:: Stripe API_VERSION: model fields audited to 2016-06-05 - @jleclanche
    """

    stripe_class = stripe.Charge
    expand_fields = ["balance_transaction"]
    stripe_dashboard_item_name = "payments"

    amount = StripeCurrencyField(help_text="Amount charged.")
    amount_refunded = StripeCurrencyField(
        help_text="Amount refunded (can be less than the amount attribute on the charge "
        "if a partial refund was issued)."
    )
    # TODO: application, application_fee, balance_transaction
    captured = StripeBooleanField(
        default=False,
        help_text="If the charge was created without capturing, this boolean represents whether or not it is still "
        "uncaptured or has since been captured."
    )
    currency = StripeCharField(
        max_length=3,
        help_text="Three-letter ISO currency code representing the currency in which the charge was made."
    )
    customer = ForeignKey(
        "Customer", on_delete=models.CASCADE, null=True,
        related_name="charges",
        help_text="The customer associated with this charge."
    )
    # XXX: destination
    account = ForeignKey(
        "Account", on_delete=models.CASCADE, null=True,
        related_name="charges",
        help_text="The account the charge was made on behalf of. Null here indicates that this value was never set."
    )
    dispute = ForeignKey(
        "Dispute", on_delete=models.SET_NULL, null=True,
        related_name="charges",
        help_text="Details about the dispute if the charge has been disputed."
    )
    failure_code = StripeEnumField(
        enum=enums.ApiErrorCode, null=True,
        help_text="Error code explaining reason for charge failure if available."
    )
    failure_message = StripeTextField(
        null=True,
        help_text="Message to user further explaining reason for charge failure if available."
    )
    fraud_details = StripeJSONField(help_text="Hash with information on fraud assessments for the charge.")
    invoice = ForeignKey(
        "Invoice", on_delete=models.CASCADE, null=True,
        related_name="charges",
        help_text="The invoice this charge is for if one exists."
    )
    # TODO: on_behalf_of, order
    outcome = StripeJSONField(help_text="Details about whether or not the payment was accepted, and why.")
    paid = StripeBooleanField(
        default=False,
        help_text="True if the charge succeeded, or was successfully authorized for later capture, False otherwise."
    )
    receipt_email = StripeCharField(
        null=True, max_length=800,  # yup, 800.
        help_text="The email address that the receipt for this charge was sent to."
    )
    receipt_number = StripeCharField(
        null=True, max_length=14,
        help_text="The transaction number that appears on email receipts sent for this charge."
    )
    refunded = StripeBooleanField(
        default=False,
        help_text="Whether or not the charge has been fully refunded. If the charge is only partially refunded, "
        "this attribute will still be false."
    )
    # TODO: review
    shipping = StripeJSONField(null=True, help_text="Shipping information for the charge")
    source = PaymentMethodForeignKey(
        on_delete=SET_NULL, null=True, related_name="charges",
        help_text="The source used for this charge."
    )
    # TODO: source_transfer
    statement_descriptor = StripeCharField(
        max_length=22, null=True,
        help_text="An arbitrary string to be displayed on your customer's credit card statement. The statement "
        "description may not include <>\"' characters, and will appear on your customer's statement in capital "
        "letters. Non-ASCII characters are automatically stripped. While most banks display this information "
        "consistently, some may display it incorrectly or not at all."
    )
    status = StripeEnumField(enum=enums.ChargeStatus, help_text="The status of the payment.")
    transfer = ForeignKey(
        "Transfer",
        null=True, on_delete=models.CASCADE,
        help_text="The transfer to the destination account (only applicable if the charge was created using the "
        "destination parameter)."
    )
    transfer_group = StripeCharField(
        max_length=255, null=True, blank=True, stripe_required=False,
        help_text="A string that identifies this transaction as part of a group."
    )

    # Everything below remains to be cleaned up
    # Balance transaction can be null if the charge failed
    fee = StripeCurrencyField(stripe_required=False, nested_name="balance_transaction")
    fee_details = StripeJSONField(stripe_required=False, nested_name="balance_transaction")

    # dj-stripe custom stripe fields. Don't try to send these.
    source_type = StripeEnumField(
        null=True,
        enum=enums.LegacySourceType,
        stripe_name="source.object",
        help_text="The payment source type. If the payment source is supported by dj-stripe, a corresponding model is "
        "attached to this Charge via a foreign key matching this field."
    )
    source_stripe_id = StripeIdField(null=True, stripe_name="source.id", help_text="The payment source id.")
    fraudulent = StripeBooleanField(default=False, help_text="Whether or not this charge was marked as fraudulent.")

    # XXX: Remove me
    receipt_sent = BooleanField(default=False, help_text="Whether or not a receipt was sent for this charge.")

    objects = ChargeManager()

    def __str__(self):
        amount = self.human_readable_amount
        status = self.human_readable_status
        if not status:
            return amount
        return "{amount} ({status})".format(amount=amount, status=status)

    @property
    def disputed(self):
        return self.dispute is not None

    @property
    def human_readable_amount(self):
        return get_friendly_currency_amount(self.amount, self.currency)

    @property
    def human_readable_status(self):
        if not self.captured:
            return "Uncaptured"
        elif self.disputed:
            return "Disputed"
        elif self.refunded:
            return "Refunded"
        elif self.amount_refunded:
            return "Partially refunded"
        elif self.status == enums.ChargeStatus.failed:
            return "Failed"

        return ""

    def _attach_objects_hook(self, cls, data):
        customer = cls._stripe_object_to_customer(target_cls=Customer, data=data)
        if customer:
            self.customer = customer

        transfer = cls._stripe_object_to_transfer(target_cls=Transfer, data=data)
        if transfer:
            self.transfer = transfer

        # Set the account on this object.
        destination_account = cls._stripe_object_destination_to_account(target_cls=Account, data=data)
        if destination_account:
            self.account = destination_account
        else:
            self.account = Account.get_default_account()

        self.source, _ = PaymentMethod._get_or_create_source(data["source"], self.source_type)

    def _calculate_refund_amount(self, amount=None):
        """
        :rtype: int
        :return: amount that can be refunded, in CENTS
        """
        eligible_to_refund = self.amount - (self.amount_refunded or 0)
        if amount:
            amount_to_refund = min(eligible_to_refund, amount)
        else:
            amount_to_refund = eligible_to_refund
        return int(amount_to_refund * 100)

    def refund(self, amount=None, reason=None):
        """
        Initiate a refund. If amount is not provided, then this will be a full refund.

        :param amount: A positive decimal amount representing how much of this charge
            to refund. Can only refund up to the unrefunded amount remaining of the charge.
        :trye amount: Decimal
        :param reason: String indicating the reason for the refund. If set, possible values
            are ``duplicate``, ``fraudulent``, and ``requested_by_customer``. Specifying
            ``fraudulent`` as the reason when you believe the charge to be fraudulent will
            help Stripe improve their fraud detection algorithms.

        :return: Stripe charge object
        :rtype: dict
        """
        charge_obj = self.api_retrieve().refund(
            amount=self._calculate_refund_amount(amount=amount),
            reason=reason,
        )
        return self.__class__.sync_from_stripe_data(charge_obj)

    def capture(self):
        """
        Capture the payment of an existing, uncaptured, charge.
        This is the second half of the two-step payment flow, where first you
        created a charge with the capture option set to False.

        See https://stripe.com/docs/api#capture_charge
        """

        captured_charge = self.api_retrieve().capture()
        return self.__class__.sync_from_stripe_data(captured_charge)

    @classmethod
    def _stripe_object_destination_to_account(cls, target_cls, data):
        """
        Search the given manager for the Account matching this Charge object's ``destination`` field.

        :param target_cls: The target class
        :type target_cls: Account
        :param data: stripe object
        :type data: dict
        """

        if "destination" in data and data["destination"]:
            return target_cls._get_or_create_from_stripe_object(data, "destination")[0]

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        # Assessments reported by you have the key user_report and, if set,
        # possible values of safe and fraudulent. Assessments from Stripe have
        # the key stripe_report and, if set, the value fraudulent.
        data["fraudulent"] = bool(data["fraud_details"]) and list(data["fraud_details"].values())[0] == "fraudulent"

        return data


@python_2_unicode_compatible
class Customer(StripeObject):
    """
    Customer objects allow you to perform recurring charges and track multiple charges that are
    associated with the same customer. (Source: https://stripe.com/docs/api/python#customers)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:

    * **object** - Unnecessary. Just check the model name.
    * **discount** - #

    .. attention:: Stripe API_VERSION: model fields and methods audited to 2017-06-05 - @jleclanche
    """

    djstripe_subscriber_key = "djstripe_subscriber"
    stripe_class = stripe.Customer
    expand_fields = ["default_source"]
    stripe_dashboard_item_name = "customers"

    account_balance = StripeIntegerField(
        help_text=(
            "Current balance, if any, being stored on the customer's account. "
            "If negative, the customer has credit to apply to the next invoice. "
            "If positive, the customer has an amount owed that will be added to the"
            "next invoice. The balance does not refer to any unpaid invoices; it "
            "solely takes into account amounts that have yet to be successfully"
            "applied to any invoice. This balance is only taken into account for "
            "recurring billing purposes (i.e., subscriptions, invoices, invoice items)."
        )
    )
    business_vat_id = StripeCharField(
        blank=True,
        max_length=20,
        null=True,
        stripe_required=False,
        help_text="The customer's VAT identification number.",
    )
    currency = StripeCharField(
        max_length=3,
        null=True,
        help_text="The currency the customer can be charged in for recurring billing purposes (subscriptions, "
        "invoices, invoice items)."
    )
    default_source = PaymentMethodForeignKey(on_delete=SET_NULL, null=True, related_name="customers")
    delinquent = StripeBooleanField(
        help_text="Whether or not the latest charge for the customer's latest invoice has failed."
    )
    # <discount>
    coupon = ForeignKey("Coupon", null=True, blank=True, on_delete=SET_NULL)
    coupon_start = StripeDateTimeField(
        null=True, editable=False, stripe_name="discount.start", stripe_required=False,
        help_text="If a coupon is present, the date at which it was applied."
    )
    coupon_end = StripeDateTimeField(
        null=True, editable=False, stripe_name="discount.end", stripe_required=False,
        help_text="If a coupon is present and has a limited duration, the date that the discount will end."
    )
    # </discount>
    email = StripeTextField(null=True)
    shipping = StripeJSONField(
        blank=True, stripe_required=False, help_text="Shipping information associated with the customer."
    )

    # dj-stripe fields
    subscriber = ForeignKey(
        djstripe_settings.get_subscriber_model_string(), null=True,
        on_delete=SET_NULL, related_name="djstripe_customers"
    )
    date_purged = DateTimeField(null=True, editable=False)

    class Meta:
        unique_together = ("subscriber", "livemode")

    def __str__(self):
        if not self.subscriber:
            return "{stripe_id} (deleted)".format(stripe_id=self.stripe_id)
        elif self.subscriber.email:
            return self.subscriber.email
        else:
            return self.stripe_id

    @classmethod
    def get_or_create(cls, subscriber, livemode=djstripe_settings.STRIPE_LIVE_MODE):
        """
        Get or create a dj-stripe customer.

        :param subscriber: The subscriber model instance for which to get or create a customer.
        :type subscriber: User

        :param livemode: Whether to get the subscriber in live or test mode.
        :type livemode: bool
        """

        try:
            return Customer.objects.get(subscriber=subscriber, livemode=livemode), False
        except Customer.DoesNotExist:
            action = "create:{}".format(subscriber.pk)
            idempotency_key = djstripe_settings.get_idempotency_key("customer", action, livemode)
            return cls.create(subscriber, idempotency_key=idempotency_key), True

    @classmethod
    def create(cls, subscriber, idempotency_key=None):
        stripe_customer = cls._api_create(
            email=subscriber.email,
            idempotency_key=idempotency_key,
            metadata={cls.djstripe_subscriber_key: subscriber.pk}
        )
        customer, created = Customer.objects.get_or_create(
            stripe_id=stripe_customer["id"],
            defaults={
                "subscriber": subscriber,
                "livemode": stripe_customer["livemode"],
                "account_balance": stripe_customer.get("account_balance", 0),
                "delinquent": stripe_customer.get("delinquent", False),
            }
        )

        return customer

    @property
    def legacy_cards(self):
        """
        Transitional property for Customer.sources.
        Use this instead of Customer.sources if you want to access the legacy Card queryset.
        """
        return self.sources

    @property
    def credits(self):
        """
        The customer is considered to have credits if their account_balance is below 0.
        """
        return abs(min(self.account_balance, 0))

    @property
    def pending_charges(self):
        """
        The customer is considered to have pending charges if their account_balance is above 0.
        """
        return max(self.account_balance, 0)

    def subscribe(
        self, plan, charge_immediately=True, application_fee_percent=None, coupon=None,
        quantity=None, metadata=None, tax_percent=None, trial_end=None, trial_from_plan=None,
        trial_period_days=None
    ):
        """
        Subscribes this customer to a plan.

        Parameters not implemented:

        * **source** - Subscriptions use the customer's default source. Including the source parameter creates \
                  a new source for this customer and overrides the default source. This functionality is not \
                  desired; add a source to the customer before attempting to add a subscription. \


        :param plan: The plan to which to subscribe the customer.
        :type plan: Plan or string (plan ID)
        :param application_fee_percent: This represents the percentage of the subscription invoice subtotal
                                        that will be transferred to the application owner's Stripe account.
                                        The request must be made with an OAuth key in order to set an
                                        application fee percentage.
        :type application_fee_percent: Decimal. Precision is 2; anything more will be ignored. A positive
                                       decimal between 1 and 100.
        :param coupon: The code of the coupon to apply to this subscription. A coupon applied to a subscription
                       will only affect invoices created for that particular subscription.
        :type coupon: string
        :param quantity: The quantity applied to this subscription. Default is 1.
        :type quantity: integer
        :param metadata: A set of key/value pairs useful for storing additional information.
        :type metadata: dict
        :param tax_percent: This represents the percentage of the subscription invoice subtotal that will
                            be calculated and added as tax to the final amount each billing period.
        :type tax_percent: Decimal. Precision is 2; anything more will be ignored. A positive decimal
                           between 1 and 100.
        :param trial_end: The end datetime of the trial period the customer will get before being charged for
                          the first time. If set, this will override the default trial period of the plan the
                          customer is being subscribed to. The special value ``now`` can be provided to end
                          the customer's trial immediately.
        :type trial_end: datetime
        :param charge_immediately: Whether or not to charge for the subscription upon creation. If False, an
                                   invoice will be created at the end of this period.
        :type charge_immediately: boolean
        :param trial_from_plan: Indicates if a plan’s trial_period_days should be applied to the subscription.
                                Setting trial_end per subscription is preferred, and this defaults to false.
                                Setting this flag to true together with trial_end is not allowed.
        :type trial_from_plan: boolean
        :param trial_period_days: Integer representing the number of trial period days before the customer is
                                  charged for the first time. This will always overwrite any trials that might
                                  apply via a subscribed plan.
        :type trial_period_days: integer

        .. Notes:
        .. ``charge_immediately`` is only available on ``Customer.subscribe()``
        .. if you're using ``Customer.subscribe()`` instead of ``Customer.subscribe()``, ``plan`` \
        can only be a string
        """

        # Convert Plan to stripe_id
        if isinstance(plan, Plan):
            plan = plan.stripe_id

        stripe_subscription = Subscription._api_create(
            plan=plan,
            customer=self.stripe_id,
            application_fee_percent=application_fee_percent,
            coupon=coupon,
            quantity=quantity,
            metadata=metadata,
            tax_percent=tax_percent,
            trial_end=trial_end,
            trial_from_plan=trial_from_plan,
            trial_period_days=trial_period_days,
        )

        if charge_immediately:
            self.send_invoice()

        return Subscription.sync_from_stripe_data(stripe_subscription)

    def charge(
        self, amount, currency=None, application_fee=None, capture=None, description=None, destination=None,
        metadata=None, shipping=None, source=None, statement_descriptor=None
    ):
        """
        Creates a charge for this customer.

        Parameters not implemented:

        * **receipt_email** - Since this is a charge on a customer, the customer's email address is used.


        :param amount: The amount to charge.
        :type amount: Decimal. Precision is 2; anything more will be ignored.
        :param currency: 3-letter ISO code for currency
        :type currency: string
        :param application_fee: A fee that will be applied to the charge and transfered to the platform owner's
                                account.
        :type application_fee: Decimal. Precision is 2; anything more will be ignored.
        :param capture: Whether or not to immediately capture the charge. When false, the charge issues an
                        authorization (or pre-authorization), and will need to be captured later. Uncaptured
                        charges expire in 7 days. Default is True
        :type capture: bool
        :param description: An arbitrary string.
        :type description: string
        :param destination: An account to make the charge on behalf of.
        :type destination: Account
        :param metadata: A set of key/value pairs useful for storing additional information.
        :type metadata: dict
        :param shipping: Shipping information for the charge.
        :type shipping: dict
        :param source: The source to use for this charge. Must be a source attributed to this customer. If None,
                       the customer's default source is used. Can be either the id of the source or the source object
                       itself.
        :type source: string, Source
        :param statement_descriptor: An arbitrary string to be displayed on the customer's credit card statement.
        :type statement_descriptor: string
        """

        if not isinstance(amount, decimal.Decimal):
            raise ValueError("You must supply a decimal value representing dollars.")

        # TODO: better default detection (should charge in customer default)
        currency = currency or "usd"

        # Convert Source to stripe_id
        if source and isinstance(source, Card):
            source = source.stripe_id

        stripe_charge = Charge._api_create(
            amount=int(amount * 100),  # Convert dollars into cents
            currency=currency,
            application_fee=int(application_fee * 100) if application_fee else None,  # Convert dollars into cents
            capture=capture,
            description=description,
            destination=destination,
            metadata=metadata,
            shipping=shipping,
            customer=self.stripe_id,
            source=source,
            statement_descriptor=statement_descriptor,
        )

        return Charge.sync_from_stripe_data(stripe_charge)

    def add_invoice_item(
        self, amount, currency, description=None, discountable=None, invoice=None,
        metadata=None, subscription=None
    ):
        """
        Adds an arbitrary charge or credit to the customer's upcoming invoice.
        Different than creating a charge. Charges are separate bills that get
        processed immediately. Invoice items are appended to the customer's next
        invoice. This is extremely useful when adding surcharges to subscriptions.

        :param amount: The amount to charge.
        :type amount: Decimal. Precision is 2; anything more will be ignored.
        :param currency: 3-letter ISO code for currency
        :type currency: string
        :param description: An arbitrary string.
        :type description: string
        :param discountable: Controls whether discounts apply to this invoice item. Defaults to False for
                             prorations or negative invoice items, and True for all other invoice items.
        :type discountable: boolean
        :param invoice: An existing invoice to add this invoice item to. When left blank, the invoice
                        item will be added to the next upcoming scheduled invoice. Use this when adding
                        invoice items in response to an ``invoice.created`` webhook. You cannot add an invoice
                        item to an invoice that has already been paid, attempted or closed.
        :type invoice: Invoice or string (invoice ID)
        :param metadata: A set of key/value pairs useful for storing additional information.
        :type metadata: dict
        :param subscription: A subscription to add this invoice item to. When left blank, the invoice
                             item will be be added to the next upcoming scheduled invoice. When set,
                             scheduled invoices for subscriptions other than the specified subscription
                             will ignore the invoice item. Use this when you want to express that an
                             invoice item has been accrued within the context of a particular subscription.
        :type subscription: Subscription or string (subscription ID)

        .. Notes:
        .. if you're using ``Customer.add_invoice_item()`` instead of ``Customer.add_invoice_item()``, \
        ``invoice`` and ``subscriptions`` can only be strings
        """

        if not isinstance(amount, decimal.Decimal):
            raise ValueError("You must supply a decimal value representing dollars.")

        # Convert Invoice to stripe_id
        if invoice is not None and isinstance(invoice, Invoice):
            invoice = invoice.stripe_id

        # Convert Subscription to stripe_id
        if subscription is not None and isinstance(subscription, Subscription):
            subscription = subscription.stripe_id

        stripe_invoiceitem = InvoiceItem._api_create(
            amount=int(amount * 100),  # Convert dollars into cents
            currency=currency,
            customer=self.stripe_id,
            description=description,
            discountable=discountable,
            invoice=invoice,
            metadata=metadata,
            subscription=subscription,
        )

        return InvoiceItem.sync_from_stripe_data(stripe_invoiceitem)

    def add_card(self, source, set_default=True):
        """
        Adds a card to this customer's account.

        :param source: Either a token, like the ones returned by our Stripe.js, or a dictionary containing a
                       user's credit card details. Stripe will automatically validate the card.
        :type source: string, dict
        :param set_default: Whether or not to set the source as the customer's default source
        :type set_default: boolean

        """

        stripe_customer = self.api_retrieve()
        new_stripe_payment_method = stripe_customer.sources.create(source=source)

        if set_default:
            stripe_customer.default_source = new_stripe_payment_method["id"]
            stripe_customer.save()

        new_payment_method = PaymentMethod.from_stripe_object(new_stripe_payment_method)

        # Change the default source
        if set_default:
            self.default_source = new_payment_method
            self.save()

        return new_payment_method.resolve()

    def purge(self):
        try:
            self._api_delete()
        except InvalidRequestError as exc:
            if "No such customer:" in text_type(exc):
                # The exception was thrown because the stripe customer was already
                # deleted on the stripe side, ignore the exception
                pass
            else:
                # The exception was raised for another reason, re-raise it
                six.reraise(*sys.exc_info())

        self.subscriber = None

        # Remove sources
        self.default_source = None
        for source in self.sources.all():
            source.remove()

        self.date_purged = timezone.now()
        self.save()

    # TODO: Override Queryset.delete() with a custom manager, since this doesn't get called in bulk deletes
    # (or cascades, but that's another matter)
    def delete(self, using=None, keep_parents=False):
        """
        Overriding the delete method to keep the customer in the records.
        All identifying information is removed via the purge() method.

        The only way to delete a customer is to use SQL.
        """

        self.purge()

    def _get_valid_subscriptions(self):
        """ Get a list of this customer's valid subscriptions."""

        return [subscription for subscription in self.subscriptions.all() if subscription.is_valid()]

    def has_active_subscription(self, plan=None):
        """
        Checks to see if this customer has an active subscription to the given plan.

        :param plan: The plan for which to check for an active subscription. If plan is None and
                     there exists only one active subscription, this method will check if that subscription
                     is valid. Calling this method with no plan and multiple valid subscriptions for this customer will
                     throw an exception.
        :type plan: Plan or string (plan ID)

        :returns: True if there exists an active subscription, False otherwise.
        :throws: TypeError if ``plan`` is None and more than one active subscription exists for this customer.
        """

        if plan is None:
            valid_subscriptions = self._get_valid_subscriptions()

            if len(valid_subscriptions) == 0:
                return False
            elif len(valid_subscriptions) == 1:
                return True
            else:
                raise TypeError("plan cannot be None if more than one valid subscription exists for this customer.")

        else:
            # Convert Plan to stripe_id
            if isinstance(plan, Plan):
                plan = plan.stripe_id

            return any([subscription.is_valid() for subscription in self.subscriptions.filter(plan__stripe_id=plan)])

    def has_any_active_subscription(self):
        """
        Checks to see if this customer has an active subscription to any plan.

        :returns: True if there exists an active subscription, False otherwise.
        :throws: TypeError if ``plan`` is None and more than one active subscription exists for this customer.
        """

        return len(self._get_valid_subscriptions()) != 0

    @property
    def active_subscriptions(self):
        """Returns active subscriptions (subscriptions with an active status that end in the future)."""
        return self.subscriptions.filter(
            status=SubscriptionStatus.active, current_period_end__gt=timezone.now()
        )

    @property
    def valid_subscriptions(self):
        """Returns this cusotmer's valid subscriptions (subscriptions that aren't cancelled."""
        return self.subscriptions.exclude(status=SubscriptionStatus.canceled)

    @property
    def subscription(self):
        """
        Shortcut to get this customer's subscription.

        :returns: None if the customer has no subscriptions, the subscription if
                  the customer has a subscription.
        :raises MultipleSubscriptionException: Raised if the customer has multiple subscriptions.
                In this case, use ``Customer.subscriptions`` instead.
        """

        subscriptions = self.valid_subscriptions

        if subscriptions.count() > 1:
            raise MultipleSubscriptionException("This customer has multiple subscriptions. Use Customer.subscriptions "
                                                "to access them.")
        else:
            return subscriptions.first()

    def can_charge(self):
        """Determines if this customer is able to be charged."""

        return self.has_valid_source() and self.date_purged is None

    def send_invoice(self):
        """
        Pay and send the customer's latest invoice.

        :returns: True if an invoice was able to be created and paid, False otherwise
                  (typically if there was nothing to invoice).
        """
        try:
            invoice = Invoice._api_create(customer=self.stripe_id)
            invoice.pay()
            return True
        except InvalidRequestError:  # TODO: Check this for a more specific error message.
            return False  # There was nothing to invoice

    def retry_unpaid_invoices(self):
        """ Attempt to retry collecting payment on the customer's unpaid invoices."""

        self._sync_invoices()
        for invoice in self.invoices.filter(paid=False, closed=False):
            try:
                invoice.retry()  # Always retry unpaid invoices
            except InvalidRequestError as exc:
                if text_type(exc) != "Invoice is already paid":
                    six.reraise(*sys.exc_info())

    def has_valid_source(self):
        """ Check whether the customer has a valid payment source."""
        return self.default_source is not None

    def add_coupon(self, coupon, idempotency_key=None):
        """
        Add a coupon to a Customer.

        The coupon can be a Coupon object, or a valid Stripe Coupon ID.
        """
        if isinstance(coupon, Coupon):
            coupon = coupon.stripe_id

        stripe_customer = self.api_retrieve()
        stripe_customer.coupon = coupon
        stripe_customer.save(idempotency_key=idempotency_key)
        return self.__class__.sync_from_stripe_data(stripe_customer)

    def upcoming_invoice(self, **kwargs):
        """ Gets the upcoming preview invoice (singular) for this customer.

        See `Invoice.upcoming() <#djstripe.Invoice.upcoming>`__.

        The ``customer`` argument to the ``upcoming()`` call is automatically set by this method.
        """

        kwargs['customer'] = self
        return Invoice.upcoming(**kwargs)

    def _attach_objects_post_save_hook(self, cls, data):  # noqa (function complexity)
        save = False

        customer_sources = data.get("sources")
        if customer_sources:
            # Have to create sources before we handle the default_source
            # We save all of them in the `sources` dict, so that we can find them
            # by id when we look at the default_source (we need the source type).
            sources = {}
            for source in customer_sources["data"]:
                obj, _ = PaymentMethod._get_or_create_source(source, source["object"])
                sources[source["id"]] = obj

        default_source = data.get("default_source")
        if default_source:
            if isinstance(default_source, six.string_types):
                default_source_id = default_source
            else:
                default_source_id = default_source["id"]
            source = sources[default_source_id]

            save = self.default_source != source
            self.default_source = source

        discount = data.get("discount")
        if discount:
            coupon, _created = Coupon._get_or_create_from_stripe_object(discount, "coupon")
            if coupon and coupon != self.coupon:
                self.coupon = coupon
                save = True
        elif self.coupon:
            self.coupon = None
            save = True

        if save:
            self.save()

    def _attach_objects_hook(self, cls, data):
        # When we save a customer to Stripe, we add a reference to its Django PK
        # in the `django_account` key. If we find that, we re-attach that PK.
        subscriber_id = data.get("metadata", {}).get(self.djstripe_subscriber_key)
        if subscriber_id:
            cls = djstripe_settings.get_subscriber_model()
            try:
                # We have to perform a get(), instead of just attaching the PK
                # blindly as the object may have been deleted or not exist.
                # Attempting to save that would cause an IntegrityError.
                self.subscriber = cls.objects.get(pk=subscriber_id)
            except (cls.DoesNotExist, ValueError):
                logger.warning("Could not find subscriber %r matching customer %r", subscriber_id, self.stripe_id)
                self.subscriber = None

    # SYNC methods should be dropped in favor of the master sync infrastructure proposed
    def _sync_invoices(self, **kwargs):
        for stripe_invoice in Invoice.api_list(customer=self.stripe_id, **kwargs):
            Invoice.sync_from_stripe_data(stripe_invoice)

    def _sync_charges(self, **kwargs):
        for stripe_charge in Charge.api_list(customer=self.stripe_id, **kwargs):
            Charge.sync_from_stripe_data(stripe_charge)

    def _sync_cards(self, **kwargs):
        for stripe_card in Card.api_list(customer=self, **kwargs):
            Card.sync_from_stripe_data(stripe_card)

    def _sync_subscriptions(self, **kwargs):
        for stripe_subscription in Subscription.api_list(customer=self.stripe_id, status="all", **kwargs):
            Subscription.sync_from_stripe_data(stripe_subscription)


class Dispute(StripeObject):
    stripe_class = stripe.Dispute
    stripe_dashboard_item_name = "disputes"

    amount = StripeIntegerField(
        help_text=(
            "Disputed amount. Usually the amount of the charge, but can differ "
            "(usually because of currency fluctuation or because only part of the order is disputed)."
        )
    )
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code.")
    evidence = StripeJSONField(help_text="Evidence provided to respond to a dispute.")
    evidence_details = StripeJSONField(help_text="Information about the evidence submission.")
    is_charge_refundable = StripeBooleanField(help_text=(
        "If true, it is still possible to refund the disputed payment. "
        "Once the payment has been fully refunded, no further funds will "
        "be withdrawn from your Stripe account as a result of this dispute."
    ))
    reason = StripeEnumField(enum=enums.DisputeReason)
    status = StripeEnumField(enum=enums.DisputeStatus)


class Event(StripeObject):
    """
    Events are POSTed to our webhook url. They provide information about a Stripe
    event that just happened. Events are processed in detail by their respective
    models (charge events by the Charge model, etc).

    **API VERSIONING**

    This is a tricky matter when it comes to webhooks. See the discussion here_.

    .. _here: https://groups.google.com/a/lists.stripe.com/forum/#!topic/api-discuss/h5Y6gzNBZp8

    In this discussion, it is noted that Webhooks are produced in one API version,
    which will usually be different from the version supported by Stripe plugins
    (such as djstripe). The solution, described there, is:

    1) validate the receipt of a webhook event by doing an event get using the
       API version of the received hook event.
    2) retrieve the referenced object (e.g. the Charge, the Customer, etc) using
       the plugin's supported API version.
    3) process that event using the retrieved object which will, only now, be in
       a format that you are certain to understand

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:

    * **object** - Unnecessary. Just check the model name.
    * **pending_webhooks** - Unnecessary. Use the dashboard.

    .. attention:: Stripe API_VERSION: model fields and methods audited to 2016-03-07 - @kavdev
    """

    stripe_class = stripe.Event
    stripe_dashboard_item_name = "events"

    api_version = StripeCharField(
        max_length=15, blank=True, help_text="the API version at which the event data was "
        "rendered. Blank for old entries only, all new entries will have this value"
    )
    data = StripeJSONField(
        help_text="data received at webhook. data should be considered to be garbage until validity check is run "
        "and valid flag is set"
    )
    request_id = StripeCharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Information about the request that triggered this event, for traceability purposes. If empty "
        "string then this is an old entry without that data. If Null then this is not an old entry, but a Stripe "
        "'automated' event with no associated request.",
        stripe_required=False
    )
    idempotency_key = StripeTextField(null=True, blank=True, stripe_required=False)
    type = StripeCharField(max_length=250, help_text="Stripe's event description code")

    def str_parts(self):
        return [
            "type={type}".format(type=self.type),
        ] + super(Event, self).str_parts()

    def _attach_objects_hook(self, cls, data):
        if self.api_version is None:
            # as of api version 2017-02-14, the account.application.deauthorized
            # event sends None as api_version.
            # If we receive that, store an empty string instead.
            # Remove this hack if this gets fixed upstream.
            self.api_version = ""

        request_obj = data.get("request", None)
        if isinstance(request_obj, dict):
            # Format as of 2017-05-25
            self.request_id = request_obj.get("request")
            self.idempotency_key = request_obj.get("idempotency_key")
        else:
            # Format before 2017-05-25
            self.request_id = request_obj

    @classmethod
    def process(cls, data):
        qs = cls.objects.filter(stripe_id=data["id"])
        if qs.exists():
            return qs.first()
        else:
            ret = cls._create_from_stripe_object(data)
            ret.invoke_webhook_handlers()
            return ret

    def invoke_webhook_handlers(self):
        """
        Invokes any webhook handlers that have been registered for this event
        based on event type or event sub-type.

        See event handlers registered in the ``djstripe.event_handlers`` module
        (or handlers registered in djstripe plugins or contrib packages).
        """

        webhooks.call_handlers(event=self)

        signal = WEBHOOK_SIGNALS.get(self.type)
        if signal:
            return signal.send(sender=Event, event=self)

    @cached_property
    def parts(self):
        """ Gets the event category/verb as a list of parts. """
        return text_type(self.type).split(".")

    @cached_property
    def category(self):
        """ Gets the event category string (e.g. 'customer'). """
        return self.parts[0]

    @cached_property
    def verb(self):
        """ Gets the event past-tense verb string (e.g. 'updated'). """
        return ".".join(self.parts[1:])

    @property
    def customer(self):
        data = self.data["object"]
        if data["object"] == "customer":
            field = "id"
        else:
            field = "customer"

        if data.get(field):
            return Customer._get_or_create_from_stripe_object(data, field)[0]


class FileUpload(StripeObject):
    filename = StripeCharField(
        max_length=255, help_text="A filename for the file, suitable for saving to a filesystem."
    )
    purpose = StripeEnumField(
        enum=enums.FileUploadPurpose, help_text="The purpose of the uploaded file."
    )
    size = StripeIntegerField(help_text="The size in bytes of the file upload object.")
    type = StripeEnumField(enum=enums.FileUploadType, help_text="The type of the file returned.")
    url = StripeCharField(
        max_length=200,
        help_text="A read-only URL where the uploaded file can be accessed."
    )


class Payout(StripeObject):
    stripe_class = stripe.Payout
    stripe_dashboard_item_name = "payouts"

    amount = StripeCurrencyField(
        help_text="Amount to be transferred to your bank account or debit card."
    )
    arrival_date = StripeDateTimeField(
        help_text=(
            "Date the payout is expected to arrive in the bank. "
            "This factors in delays like weekends or bank holidays."
        )
    )
    # TODO: balance_transaction = ForeignKey("Transaction")  txn_...
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code.")
    destination = models.ForeignKey(
        "BankAccount", on_delete=models.PROTECT, null=True,
        help_text="ID of the bank account or card the payout was sent to."
    )
    # TODO: failure_balance_transaction = ForeignKey("Transaction", null=True)
    failure_code = StripeEnumField(
        enum=enums.PayoutFailureCode,
        blank=True, null=True,
        help_text="Error code explaining reason for transfer failure if available. "
        "See https://stripe.com/docs/api/python#transfer_failures."
    )
    failure_message = StripeTextField(
        null=True, blank=True,
        help_text="Message to user further explaining reason for payout failure if available."
    )
    method = StripeEnumField(max_length=8, enum=enums.PayoutMethod, help_text=(
        "The method used to send this payout. "
        "`instant` is only supported for payouts to debit cards."
    ))
    # TODO: source_type
    statement_descriptor = StripeCharField(
        max_length=255, null=True, blank=True,
        help_text="Extra information about a payout to be displayed on the user's bank statement."
    )
    status = StripeEnumField(enum=enums.PayoutStatus, help_text=(
        "Current status of the payout. "
        "A payout will be `pending` until it is submitted to the bank, at which point it "
        "becomes `in_transit`. I t will then change to paid if the transaction goes through. "
        "If it does not go through successfully, its status will change to `failed` or `canceled`."
    ))
    type = StripeEnumField(enum=enums.PayoutType)


class Refund(StripeObject):
    """
    https://stripe.com/docs/api#refund_object
    https://stripe.com/docs/refunds
    """
    stripe_class = stripe.Refund

    amount = StripeIntegerField(help_text="Amount, in cents.")
    # balance_transaction = ForeignKey("BalanceTransaction")
    charge = ForeignKey(
        "Charge", on_delete=models.CASCADE, related_name="refunds",
        help_text="The charge that was refunded"
    )
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code")
    # failure_balance_transaction = ForeignKey("BalanceTransaction", null=True)
    failure_reason = StripeEnumField(
        enum=enums.RefundFailureReason, stripe_required=False,
        help_text="If the refund failed, the reason for refund failure if known."
    )
    reason = StripeEnumField(
        enum=enums.RefundReason, null=True, help_text="Reason for the refund."
    )
    receipt_number = StripeCharField(max_length=9, null=True, help_text=(
        "The transaction number that appears on email receipts sent for this charge."
    ))
    status = StripeEnumField(enum=enums.RefundFailureReason, help_text="Status of the refund.")

    def get_stripe_dashboard_url(self):
        return self.charge.get_stripe_dashboard_url()

    def _attach_objects_hook(self, cls, data):
        self.charge = Charge._get_or_create_from_stripe_object(data, "charge")[0]


# ============================================================================ #
#                               Payment Methods                                #
# ============================================================================ #


class BankAccount(StripeObject):
    account = ForeignKey(
        "Account", on_delete=models.PROTECT,
        related_name="bank_account",
        help_text="The account the charge was made on behalf of. Null here indicates that this value was never set."
    )
    account_holder_name = StripeCharField(
        max_length=5000, null=True,
        help_text="The name of the person or business that owns the bank account."
    )
    account_holder_type = StripeEnumField(
        enum=enums.BankAccountHolderType, help_text="The type of entity that holds the account."
    )
    bank_name = StripeCharField(
        max_length=255,
        help_text="Name of the bank associated with the routing number (e.g., `WELLS FARGO`)."
    )
    country = StripeCharField(
        max_length=2,
        help_text="Two-letter ISO code representing the country the bank account is located in."
    )
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code")
    customer = models.ForeignKey(
        "Customer", on_delete=models.SET_NULL, null=True, related_name="bank_account"
    )
    default_for_currency = StripeNullBooleanField(
        help_text="Whether this external account is the default account for its currency."
    )
    fingerprint = StripeCharField(
        max_length=16,
        help_text=(
            "Uniquely identifies this particular bank account. "
            "You can use this attribute to check whether two bank accounts are the same."
        )
    )
    last4 = StripeCharField(max_length=4)
    routing_number = StripeCharField(max_length=255, help_text="The routing transit number for the bank account.")
    status = StripeEnumField(enum=enums.BankAccountStatus)


class Card(StripeObject):
    """
    You can store multiple cards on a customer in order to charge the customer later.
    (Source: https://stripe.com/docs/api/python#cards)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:

    * **object** -  Unnecessary. Just check the model name.
    * **recipient** -  On Stripe's deprecation path.
    * **account** -  #
    * **currency** -  #
    * **default_for_currency** -  #

    .. attention:: Stripe API_VERSION: model fields and methods audited to 2016-03-07 - @kavdev
    """

    stripe_class = stripe.Card

    address_city = StripeTextField(null=True, help_text="Billing address city.")
    address_country = StripeTextField(null=True, help_text="Billing address country.")
    address_line1 = StripeTextField(null=True, help_text="Billing address (Line 1).")
    address_line1_check = StripeEnumField(enum=enums.CardCheckResult, null=True, help_text=(
        "If `address_line1` was provided, results of the check."
    ))
    address_line2 = StripeTextField(null=True, help_text="Billing address (Line 2).")
    address_state = StripeTextField(null=True, help_text="Billing address state.")
    address_zip = StripeTextField(null=True, help_text="Billing address zip code.")
    address_zip_check = StripeEnumField(enum=enums.CardCheckResult, null=True, help_text=(
        "If `address_zip` was provided, results of the check."
    ))
    brand = StripeEnumField(enum=enums.CardBrand, help_text="Card brand.")
    country = StripeCharField(
        null=True,
        max_length=2,
        help_text="Two-letter ISO code representing the country of the card."
    )
    cvc_check = StripeEnumField(enum=enums.CardCheckResult, null=True, help_text=(
        "If a CVC was provided, results of the check."
    ))
    dynamic_last4 = StripeCharField(
        null=True,
        max_length=4,
        help_text="(For tokenized numbers only.) The last four digits of the device account number."
    )
    exp_month = StripeIntegerField(help_text="Card expiration month.")
    exp_year = StripeIntegerField(help_text="Card expiration year.")
    fingerprint = StripeTextField(
        stripe_required=False, help_text="Uniquely identifies this particular card number."
    )
    funding = StripeEnumField(enum=enums.CardFundingType, help_text="Card funding type.")
    last4 = StripeCharField(max_length=4, help_text="Last four digits of Card number.")
    name = StripeTextField(null=True, help_text="Cardholder name.")
    tokenization_method = StripeEnumField(
        enum=enums.CardTokenizationMethod, null=True,
        help_text="If the card number is tokenized, this is the method that was used."
    )

    customer = models.ForeignKey(
        "Customer", on_delete=models.CASCADE, related_name="sources"
    )

    @staticmethod
    def _get_customer_from_kwargs(**kwargs):
        if "customer" not in kwargs or not isinstance(kwargs["customer"], Customer):
            raise StripeObjectManipulationException("Cards must be manipulated through a Customer. "
                                                    "Pass a Customer object into this call.")

        customer = kwargs["customer"]
        del kwargs["customer"]

        return customer, kwargs

    @classmethod
    def _api_create(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        # OVERRIDING the parent version of this function
        # Cards must be manipulated through a customer or account.
        # TODO: When managed accounts are supported, this method needs to check if either a customer or
        #       account is supplied to determine the correct object to use.

        customer, clean_kwargs = cls._get_customer_from_kwargs(**kwargs)

        return customer.api_retrieve().sources.create(api_key=api_key, **clean_kwargs)

    @classmethod
    def api_list(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs):
        # OVERRIDING the parent version of this function
        # Cards must be manipulated through a customer or account.
        # TODO: When managed accounts are supported, this method needs to check if either a customer or
        #       account is supplied to determine the correct object to use.

        customer, clean_kwargs = cls._get_customer_from_kwargs(**kwargs)

        return customer.api_retrieve(api_key=api_key).sources.list(object="card", **clean_kwargs).auto_paging_iter()

    def _attach_objects_hook(self, cls, data):
        customer = cls._stripe_object_to_customer(target_cls=Customer, data=data)
        if customer:
            self.customer = customer
        else:
            raise ValidationError("A customer was not attached to this card.")

    def get_stripe_dashboard_url(self):
        return self.customer.get_stripe_dashboard_url()

    def remove(self):
        """Removes a card from this customer's account."""

        # First, wipe default source on all customers that use this card.
        Customer.objects.filter(default_source=self.stripe_id).update(default_source=None)

        try:
            self._api_delete()
        except InvalidRequestError as exc:
            if "No such source:" in text_type(exc) or "No such customer:" in text_type(exc):
                # The exception was thrown because the stripe customer or card was already
                # deleted on the stripe side, ignore the exception
                pass
            else:
                # The exception was raised for another reason, re-raise it
                six.reraise(*sys.exc_info())

        self.delete()

    def api_retrieve(self, api_key=None):
        # OVERRIDING the parent version of this function
        # Cards must be manipulated through a customer or account.
        # TODO: When managed accounts are supported, this method needs to check if
        # either a customer or account is supplied to determine the correct object to use.
        api_key = api_key or self.default_api_key
        customer = self.customer.api_retrieve(api_key=api_key)

        # If the customer is deleted, the sources attribute will be absent.
        # eg. {"id": "cus_XXXXXXXX", "deleted": True}
        if "sources" not in customer:
            # We fake a native stripe InvalidRequestError so that it's caught like an invalid ID error.
            raise InvalidRequestError("No such source: %s" % (self.stripe_id), "id")

        return customer.sources.retrieve(self.stripe_id, expand=self.expand_fields)

    def str_parts(self):
        return [
            "brand={brand}".format(brand=self.brand),
            "last4={last4}".format(last4=self.last4),
            "exp_month={exp_month}".format(exp_month=self.exp_month),
            "exp_year={exp_year}".format(exp_year=self.exp_year),
        ] + super(Card, self).str_parts()

    @classmethod
    def create_token(
        cls, number, exp_month, exp_year, cvc,
        api_key=djstripe_settings.STRIPE_SECRET_KEY, **kwargs
    ):
        """
        Creates a single use token that wraps the details of a credit card. This token can be used in
        place of a credit card dictionary with any API method. These tokens can only be used once: by
        creating a new charge object, or attaching them to a customer.
        (Source: https://stripe.com/docs/api/python#create_card_token)

        :param exp_month: The card's expiration month.
        :type exp_month: Two digit int
        :param exp_year: The card's expiration year.
        :type exp_year: Two or Four digit int
        :param number: The card number
        :type number: string without any separators (no spaces)
        :param cvc: Card security code.
        :type cvc: string
        """

        card = {
            "number": number,
            "exp_month": exp_month,
            "exp_year": exp_year,
            "cvc": cvc,
        }
        card.update(kwargs)

        return stripe.Token.create(api_key=api_key, card=card)


# Backwards compatibility
StripeSource = Card


class Source(StripeObject):
    amount = StripeCurrencyField(null=True, blank=True, help_text=(
        "Amount associated with the source. "
        "This is the amount for which the source will be chargeable once ready. "
        "Required for `single_use` sources."
    ))
    client_secret = StripeCharField(max_length=255, help_text=(
        "The client secret of the source. "
        "Used for client-side retrieval using a publishable key."
    ))
    currency = StripeCharField(null=True, blank=True, max_length=3, help_text="Three-letter ISO currency code")
    flow = StripeEnumField(enum=enums.SourceFlow, help_text=(
        "The authentication flow of the source."
    ))
    owner = StripeJSONField(help_text=(
        "Information about the owner of the payment instrument that may be "
        "used or required by particular source types."
    ))
    statement_descriptor = StripeCharField(
        null=True, blank=True, max_length=255, help_text=(
            "Extra information about a source. "
            "This will appear on your customer's statement every time you charge the source."
        )
    )
    status = StripeEnumField(enum=enums.SourceStatus, help_text=(
        "The status of the source. Only `chargeable` sources can be used to create a charge."
    ))
    type = StripeEnumField(enum=enums.SourceType, help_text="The type of the source.")
    usage = StripeEnumField(enum=enums.SourceUsage, help_text=(
        "Whether this source should be reusable or not. "
        "Some source types may or may not be reusable by construction, "
        "while other may leave the option at creation."
    ))

    # Flows
    code_verification = StripeJSONField(
        null=True, blank=True, stripe_required=False, help_text=(
            "Information related to the code verification flow. "
            "Present if the source is authenticated by a verification code (`flow` is `code_verification`)."
        )
    )
    receiver = StripeJSONField(
        null=True, blank=True, stripe_required=False, help_text=(
            "Information related to the receiver flow. "
            "Present if the source is a receiver (`flow` is `receiver`)."
        )
    )
    redirect = StripeJSONField(
        null=True, blank=True, stripe_required=False, help_text=(
            "Information related to the redirect flow. "
            "Present if the source is authenticated by a redirect (`flow` is `redirect`)."
        )
    )

    source_data = StripeJSONField(help_text=(
        "The data corresponding to the source type."
    ))

    customer = models.ForeignKey(
        "Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="sources_v3"
    )

    stripe_class = stripe.Source
    stripe_dashboard_item_name = "sources"

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        # The source_data dict is an alias of all the source types
        data["source_data"] = data[data["type"]]
        return data

    def _attach_objects_hook(self, cls, data):
        customer = cls._stripe_object_to_customer(target_cls=Customer, data=data)
        if customer:
            self.customer = customer
        else:
            self.customer = None

    def detach(self):
        """
        Detach the source from its customer.
        """

        # First, wipe default source on all customers that use this.
        Customer.objects.filter(default_source=self.stripe_id).update(default_source=None)

        try:
            self.sync_from_stripe_data(self.api_retrieve().detach())
            return True
        except (InvalidRequestError, NotImplementedError):
            # The source was already detached. Resyncing.
            # NotImplementedError is an artifact of stripe-python<2.0
            # https://github.com/stripe/stripe-python/issues/376
            self.sync_from_stripe_data(self.api_retrieve())
            return False


# ============================================================================ #
#                                Subscriptions                                 #
# ============================================================================ #


@python_2_unicode_compatible
class Coupon(StripeObject):
    stripe_id = StripeIdField(stripe_name="id", max_length=500)
    amount_off = StripeCurrencyField(
        null=True, blank=True,
        help_text="Amount that will be taken off the subtotal of any invoices for this customer."
    )
    currency = StripeCharField(null=True, blank=True, max_length=3, help_text="Three-letter ISO currency code")
    duration = StripeEnumField(enum=enums.CouponDuration, help_text=(
        "Describes how long a customer who applies this coupon will get the discount."
    ))
    duration_in_months = StripePositiveIntegerField(
        null=True, blank=True,
        help_text="If `duration` is `repeating`, the number of months the coupon applies."
    )
    max_redemptions = StripePositiveIntegerField(
        null=True, blank=True,
        help_text="Maximum number of times this coupon can be redeemed, in total, before it is no longer valid."
    )
    # This is not a StripePercentField. Only integer values between 1 and 100 are possible.
    percent_off = StripePositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    redeem_by = StripeDateTimeField(
        null=True, blank=True,
        help_text="Date after which the coupon can no longer be redeemed. Max 5 years in the future."
    )
    times_redeemed = StripePositiveIntegerField(
        editable=False, default=0,
        help_text="Number of times this coupon has been applied to a customer."
    )
    # valid = StripeBooleanField(editable=False)

    # XXX
    DURATION_FOREVER = "forever"
    DURATION_ONCE = "once"
    DURATION_REPEATING = "repeating"

    class Meta:
        unique_together = ("stripe_id", "livemode")

    stripe_class = stripe.Coupon
    stripe_dashboard_item_name = "coupons"

    def __str__(self):
        return self.human_readable

    @property
    def human_readable_amount(self):
        if self.percent_off:
            amount = "{percent_off}%".format(percent_off=self.percent_off)
        else:
            amount = get_friendly_currency_amount(self.amount_off or 0, self.currency)
        return "{amount} off".format(amount=amount)

    @property
    def human_readable(self):
        if self.duration == self.DURATION_REPEATING:
            if self.duration_in_months == 1:
                duration = "for {duration_in_months} month"
            else:
                duration = "for {duration_in_months} months"
            duration = duration.format(duration_in_months=self.duration_in_months)
        else:
            duration = self.duration
        return "{amount} {duration}".format(amount=self.human_readable_amount, duration=duration)


@python_2_unicode_compatible
class Invoice(StripeObject):
    """
    Invoices are statements of what a customer owes for a particular billing
    period, including subscriptions, invoice items, and any automatic proration
    adjustments if necessary.

    Once an invoice is created, payment is automatically attempted. Note that
    the payment, while automatic, does not happen exactly at the time of invoice
    creation. If you have configured webhooks, the invoice will wait until one
    hour after the last webhook is successfully sent (or the last webhook times
    out after failing).

    Any customer credit on the account is applied before determining how much is
    due for that invoice (the amount that will be actually charged).
    If the amount due for the invoice is less than 50 cents (the minimum for a
    charge), we add the amount to the customer's running account balance to be
    added to the next invoice. If this amount is negative, it will act as a
    credit to offset the next invoice. Note that the customer account balance
    does not include unpaid invoices; it only includes balances that need to be
    taken into account when calculating the amount due for the next invoice.
    (Source: https://stripe.com/docs/api/python#invoices)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:

    * **object** - Unnecessary. Just check the model name.
    * **discount** - #
    * **lines** - Unnecessary. Check Subscription and InvoiceItems directly.
    * **webhooks_delivered_at** - #

    .. attention:: Stripe API_VERSION: model fields audited to 2017-06-05 - @jleclanche
    """

    stripe_class = stripe.Invoice
    stripe_dashboard_item_name = "invoices"

    amount_due = StripeCurrencyField(
        help_text="Final amount due at this time for this invoice. If the invoice's total is smaller than the minimum "
        "charge amount, for example, or if there is account credit that can be applied to the invoice, the amount_due "
        "may be 0. If there is a positive starting_balance for the invoice (the customer owes money), the amount_due "
        "will also take that into account. The charge that gets generated for the invoice will be for the amount "
        "specified in amount_due."
    )
    amount_paid = StripeCurrencyField(
        null=True,  # XXX: This is not nullable, but it's a new field
        help_text="The amount, in cents, that was paid."
    )
    amount_remaining = StripeCurrencyField(
        null=True,  # XXX: This is not nullable, but it's a new field
        help_text="The amount, in cents, that was paid."
    )
    application_fee = StripeCurrencyField(
        null=True,
        help_text="The fee in cents that will be applied to the invoice and transferred to the application owner's "
        "Stripe account when the invoice is paid."
    )
    attempt_count = StripeIntegerField(
        help_text="Number of payment attempts made for this invoice, from the perspective of the payment retry "
        "schedule. Any payment attempt counts as the first attempt, and subsequently only automatic retries "
        "increment the attempt count. In other words, manual payment attempts after the first attempt do not affect "
        "the retry schedule."
    )
    attempted = StripeBooleanField(
        default=False,
        help_text="Whether or not an attempt has been made to pay the invoice. An invoice is not attempted until 1 "
        "hour after the ``invoice.created`` webhook, for example, so you might not want to display that invoice as "
        "unpaid to your users."
    )
    billing = StripeEnumField(enum=enums.InvoiceBilling, null=True, help_text=(
        "When charging automatically, Stripe will attempt to pay this invoice"
        "using the default source attached to the customer. "
        "When sending an invoice, Stripe will email this invoice to the customer "
        "with payment instructions."
    ))
    charge = OneToOneField(
        Charge,
        null=True, on_delete=models.CASCADE,
        related_name="latest_invoice",
        help_text="The latest charge generated for this invoice, if any."
    )
    closed = StripeBooleanField(
        default=False,
        help_text="Whether or not the invoice is still trying to collect payment. An invoice is closed if it's either "
        "paid or it has been marked closed. A closed invoice will no longer attempt to collect payment."
    )
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code.")
    customer = ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name="invoices",
        help_text="The customer associated with this invoice."
    )
    date = StripeDateTimeField(help_text="The date on the invoice.")
    # TODO: discount
    due_date = StripeDateTimeField(null=True, help_text=(
        "The date on which payment for this invoice is due. "
        "This value will be null for invoices where billing=charge_automatically."
    ))
    ending_balance = StripeIntegerField(
        null=True,
        help_text="Ending customer balance after attempting to pay invoice. If the invoice has not been attempted "
        "yet, this will be null."
    )
    forgiven = StripeBooleanField(
        default=False,
        help_text="Whether or not the invoice has been forgiven. Forgiving an invoice instructs us to update the "
        "subscription status as if the invoice were successfully paid. Once an invoice has been forgiven, it cannot "
        "be unforgiven or reopened."
    )
    hosted_invoice_url = StripeCharField(max_length=799, stripe_required=False, help_text=(
        "The URL for the hosted invoice page, which allows customers to view and pay an invoice. "
        "If the invoice has not been frozen yet, this will be null."
    ))
    invoice_pdf = StripeCharField(max_length=799, stripe_required=False, help_text=(
        "The link to download the PDF for the invoice. "
        "If the invoice has not been frozen yet, this will be null."
    ))
    next_payment_attempt = StripeDateTimeField(
        null=True,
        help_text="The time at which payment will next be attempted."
    )
    number = StripeCharField(max_length=64, null=True, help_text=(
        "A unique, identifying string that appears on emails sent to the customer for this invoice. "
        "This starts with the customer’s unique invoice_prefix if it is specified."
    ))
    paid = StripeBooleanField(
        default=False,
        help_text="The time at which payment will next be attempted."
    )
    period_end = StripeDateTimeField(
        help_text="End of the usage period during which invoice items were added to this invoice."
    )
    period_start = StripeDateTimeField(
        help_text="Start of the usage period during which invoice items were added to this invoice."
    )
    receipt_number = StripeCharField(max_length=64, null=True, help_text=(
        "This is the transaction number that appears on email receipts sent for this invoice."
    ))
    starting_balance = StripeIntegerField(
        help_text="Starting customer balance before attempting to pay invoice. If the invoice has not been attempted "
        "yet, this will be the current customer balance."
    )
    statement_descriptor = StripeCharField(
        max_length=22,
        null=True,
        help_text="An arbitrary string to be displayed on your customer's credit card statement. The statement "
        "description may not include <>\"' characters, and will appear on your customer's statement in capital "
        "letters. Non-ASCII characters are automatically stripped. While most banks display this information "
        "consistently, some may display it incorrectly or not at all."
    )
    subscription = ForeignKey(
        "Subscription",
        null=True,
        related_name="invoices",
        on_delete=SET_NULL,
        help_text="The subscription that this invoice was prepared for, if any."
    )
    subscription_proration_date = StripeDateTimeField(
        stripe_required=False,
        help_text="Only set for upcoming invoices that preview prorations. The time used to calculate prorations."
    )
    subtotal = StripeCurrencyField(
        help_text="Only set for upcoming invoices that preview prorations. The time used to calculate prorations."
    )
    tax = StripeCurrencyField(
        null=True,
        help_text="The amount of tax included in the total, calculated from ``tax_percent`` and the subtotal. If no "
        "``tax_percent`` is defined, this value will be null."
    )
    tax_percent = StripePercentField(
        null=True,
        help_text="This percentage of the subtotal has been added to the total amount of the invoice, including "
        "invoice line items and discounts. This field is inherited from the subscription's ``tax_percent`` field, "
        "but can be changed before the invoice is paid. This field defaults to null."
    )
    total = StripeCurrencyField("Total after discount.")
    webhooks_delivered_at = StripeDateTimeField(null=True, help_text=(
        "The time at which webhooks for this invoice were successfully delivered "
        "(if the invoice had no webhooks to deliver, this will match `date`). "
        "Invoice payment is delayed until webhooks are delivered, or until all "
        "webhook delivery attempts have been exhausted."
    ))

    class Meta(object):
        ordering = ["-date"]

    def __str__(self):
        return "Invoice #{number}".format(number=self.number or self.receipt_number or self.stripe_id)

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        data = super(Invoice, cls)._manipulate_stripe_object_hook(data)
        # fixup fields to maintain compatibility while avoiding a database migration on the stable branch

        # deprecated in API 2018-11-08 - see https://stripe.com/docs/upgrades#2018-11-08
        if "closed" not in data:
            # https://stripe.com/docs/billing/invoices/migrating-new-invoice-states#autoadvance
            if "auto_advance" in data:
                data["closed"] = not data["auto_advance"]
            else:
                data["closed"] = False

        if "forgiven" not in data:
            if "status" in data:
                data["forgiven"] = data["status"] == "uncollectible"
            else:
                data["forgiven"] = False

        return data

    @classmethod
    def _stripe_object_to_charge(cls, target_cls, data):
        """
        Search the given manager for the Charge matching this object's ``charge`` field.

        :param target_cls: The target class
        :type target_cls: Charge
        :param data: stripe object
        :type data: dict
        """

        if "charge" in data and data["charge"]:
            return target_cls._get_or_create_from_stripe_object(data, "charge")[0]

    @classmethod
    def upcoming(
        cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, customer=None, coupon=None, subscription=None,
        subscription_plan=None, subscription_prorate=None, subscription_proration_date=None,
        subscription_quantity=None, subscription_trial_end=None, **kwargs
    ):
        """
        Gets the upcoming preview invoice (singular) for a customer.

        At any time, you can preview the upcoming
        invoice for a customer. This will show you all the charges that are
        pending, including subscription renewal charges, invoice item charges,
        etc. It will also show you any discount that is applicable to the
        customer. (Source: https://stripe.com/docs/api#upcoming_invoice)

        .. important:: Note that when you are viewing an upcoming invoice, you are simply viewing a preview.

        :param customer: The identifier of the customer whose upcoming invoice \
        you'd like to retrieve.
        :type customer: Customer or string (customer ID)
        :param coupon: The code of the coupon to apply.
        :type coupon: str
        :param subscription: The identifier of the subscription to retrieve an \
        invoice for.
        :type subscription: Subscription or string (subscription ID)
        :param subscription_plan: If set, the invoice returned will preview \
        updating the subscription given to this plan, or creating a new \
        subscription to this plan if no subscription is given.
        :type subscription_plan: Plan or string (plan ID)
        :param subscription_prorate: If previewing an update to a subscription, \
        this decides whether the preview will show the result of applying \
        prorations or not.
        :type subscription_prorate: bool
        :param subscription_proration_date: If previewing an update to a \
        subscription, and doing proration, subscription_proration_date forces \
        the proration to be calculated as though the update was done at the \
        specified time.
        :type subscription_proration_date: datetime
        :param subscription_quantity: If provided, the invoice returned will \
        preview updating or creating a subscription with that quantity.
        :type subscription_quantity: int
        :param subscription_trial_end: If provided, the invoice returned will \
        preview updating or creating a subscription with that trial end.
        :type subscription_trial_end: datetime
        :returns: The upcoming preview invoice.
        :rtype: UpcomingInvoice
        """

        # Convert Customer to stripe_id
        if customer is not None and isinstance(customer, Customer):
            customer = customer.stripe_id

        # Convert Subscription to stripe_id
        if subscription is not None and isinstance(subscription, Subscription):
            subscription = subscription.stripe_id

        # Convert Plan to stripe_id
        if subscription_plan is not None and isinstance(subscription_plan, Plan):
            subscription_plan = subscription_plan.stripe_id

        try:
            upcoming_stripe_invoice = cls.stripe_class.upcoming(
                api_key=api_key, customer=customer,
                coupon=coupon, subscription=subscription,
                subscription_plan=subscription_plan,
                subscription_prorate=subscription_prorate,
                subscription_proration_date=subscription_proration_date,
                subscription_quantity=subscription_quantity,
                subscription_trial_end=subscription_trial_end, **kwargs)
        except InvalidRequestError as exc:
            if text_type(exc) != "Nothing to invoice for customer":
                six.reraise(*sys.exc_info())
            return

        # Workaround for "id" being missing (upcoming invoices don't persist).
        upcoming_stripe_invoice["id"] = "upcoming"

        return UpcomingInvoice._create_from_stripe_object(upcoming_stripe_invoice, save=False)

    def retry(self):
        """ Retry payment on this invoice if it isn't paid, closed, or forgiven."""

        if not self.paid and not self.forgiven and not self.closed:
            stripe_invoice = self.api_retrieve()
            updated_stripe_invoice = stripe_invoice.pay()  # pay() throws an exception if the charge is not successful.
            type(self).sync_from_stripe_data(updated_stripe_invoice)
            return True
        return False

    STATUS_PAID = "Paid"
    STATUS_FORGIVEN = "Forgiven"
    STATUS_CLOSED = "Closed"
    STATUS_OPEN = "Open"

    @property
    def status(self):
        """ Attempts to label this invoice with a status. Note that an invoice can be more than one of the choices.
            We just set a priority on which status appears.
        """

        if self.paid:
            return self.STATUS_PAID
        if self.forgiven:
            return self.STATUS_FORGIVEN
        if self.closed:
            return self.STATUS_CLOSED
        return self.STATUS_OPEN

    def get_stripe_dashboard_url(self):
        return self.customer.get_stripe_dashboard_url()

    def _attach_objects_hook(self, cls, data):
        self.customer = cls._stripe_object_to_customer(target_cls=Customer, data=data)

        charge = cls._stripe_object_to_charge(target_cls=Charge, data=data)
        if charge:
            self.charge = charge

        subscription = cls._stripe_object_to_subscription(target_cls=Subscription, data=data)
        if subscription:
            self.subscription = subscription

    def _attach_objects_post_save_hook(self, cls, data):
        # InvoiceItems need a saved invoice because they're associated via a
        # RelatedManager, so this must be done as part of the post save hook.
        cls._stripe_object_to_invoice_items(target_cls=InvoiceItem, data=data, invoice=self)

    @property
    def plan(self):
        """ Gets the associated plan for this invoice.

        In order to provide a consistent view of invoices, the plan object
        should be taken from the first invoice item that has one, rather than
        using the plan associated with the subscription.

        Subscriptions (and their associated plan) are updated by the customer
        and represent what is current, but invoice items are immutable within
        the invoice and stay static/unchanged.

        In other words, a plan retrieved from an invoice item will represent
        the plan as it was at the time an invoice was issued.  The plan
        retrieved from the subscription will be the currently active plan.

        :returns: The associated plan for the invoice.
        :rtype: ``djstripe.Plan``
        """

        for invoiceitem in self.invoiceitems.all():
            if invoiceitem.plan:
                return invoiceitem.plan

        if self.subscription:
            return self.subscription.plan


class UpcomingInvoice(Invoice):
    def __init__(self, *args, **kwargs):
        super(UpcomingInvoice, self).__init__(*args, **kwargs)
        self._invoiceitems = []

    def get_stripe_dashboard_url(self):
        return ""

    def _attach_objects_hook(self, cls, data):
        super(UpcomingInvoice, self)._attach_objects_hook(cls, data)
        self._invoiceitems = cls._stripe_object_to_invoice_items(target_cls=InvoiceItem, data=data, invoice=self)

    @property
    def invoiceitems(self):
        """ Gets the invoice items associated with this upcoming invoice.

        This differs from normal (non-upcoming) invoices, in that upcoming
        invoices are in-memory and do not persist to the database. Therefore,
        all of the data comes from the Stripe API itself.

        Instead of returning a normal queryset for the invoiceitems, this will
        return a mock of a queryset, but with the data fetched from Stripe - It
        will act like a normal queryset, but mutation will silently fail.
        """

        return QuerySetMock.from_iterable(InvoiceItem, self._invoiceitems)

    @property
    def stripe_id(self):
        return None

    @stripe_id.setter
    def stripe_id(self, value):
        return  # noop

    def save(self, *args, **kwargs):
        return  # noop


@python_2_unicode_compatible
class InvoiceItem(StripeObject):
    """
    Sometimes you want to add a charge or credit to a customer but only actually charge the customer's
    card at the end of a regular billing cycle. This is useful for combining several charges to
    minimize per-transaction fees or having Stripe tabulate your usage-based billing totals.
    (Source: https://stripe.com/docs/api/python#invoiceitems)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:

    * **object** - Unnecessary. Just check the model name.

    .. attention:: Stripe API_VERSION: model fields audited to 2017-06-05 - @jleclanche
    """

    stripe_class = stripe.InvoiceItem

    amount = StripeCurrencyField(help_text="Amount invoiced.")
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code.")
    customer = ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name="invoiceitems",
        help_text="The customer associated with this invoiceitem."
    )
    date = StripeDateTimeField(help_text="The date on the invoiceitem.")
    discountable = StripeBooleanField(
        default=False,
        help_text="If True, discounts will apply to this invoice item. Always False for prorations."
    )
    invoice = ForeignKey(
        Invoice, on_delete=models.CASCADE,
        null=True,
        related_name="invoiceitems",
        help_text="The invoice to which this invoiceitem is attached."
    )
    period = StripeJSONField()
    period_end = StripeDateTimeField(
        stripe_name="period.end",
        help_text="Might be the date when this invoiceitem's invoice was sent."
    )
    period_start = StripeDateTimeField(
        stripe_name="period.start",
        help_text="Might be the date when this invoiceitem was added to the invoice"
    )
    plan = ForeignKey(
        "Plan",
        null=True,
        related_name="invoiceitems",
        on_delete=SET_NULL,
        help_text="If the invoice item is a proration, the plan of the subscription for which the proration was "
        "computed."
    )
    proration = StripeBooleanField(
        default=False,
        help_text="Whether or not the invoice item was created automatically as a proration adjustment when the "
        "customer switched plans."
    )
    quantity = StripeIntegerField(
        stripe_required=False,
        help_text="If the invoice item is a proration, the quantity of the subscription for which the proration "
        "was computed."
    )
    subscription = ForeignKey(
        "Subscription",
        null=True,
        related_name="invoiceitems",
        on_delete=SET_NULL,
        help_text="The subscription that this invoice item has been created for, if any."
    )
    # XXX: subscription_item

    @classmethod
    def _stripe_object_to_plan(cls, target_cls, data):
        """
        Search the given manager for the Plan matching this Charge object's ``plan`` field.

        :param target_cls: The target class
        :type target_cls: Plan
        :param data: stripe object
        :type data: dict
        """

        if "plan" in data and data["plan"]:
            return target_cls._get_or_create_from_stripe_object(data, "plan")[0]

    def __str__(self):
        if self.plan and self.plan.product:
            return self.plan.product.name or text_type(self.plan)
        # See: https://code.djangoproject.com/ticket/25218
        text_method = '__str__' if PY3 else '__unicode__'
        return getattr(super(InvoiceItem, self), text_method)()

    def _attach_objects_hook(self, cls, data):
        customer = cls._stripe_object_to_customer(target_cls=Customer, data=data)

        invoice = cls._stripe_object_to_invoice(target_cls=Invoice, data=data)
        if invoice:
            self.invoice = invoice
            customer = customer or invoice.customer

        plan = cls._stripe_object_to_plan(target_cls=Plan, data=data)
        if plan:
            self.plan = plan

        subscription = cls._stripe_object_to_subscription(target_cls=Subscription, data=data)
        if subscription:
            self.subscription = subscription
            customer = customer or subscription.customer

        self.customer = customer

    def get_stripe_dashboard_url(self):
        return self.invoice.get_stripe_dashboard_url()

    def str_parts(self):
        return [
            "amount={amount}".format(amount=self.amount),
            "date={date}".format(date=self.date),
        ] + super(InvoiceItem, self).str_parts()


@python_2_unicode_compatible
class Plan(StripeObject):
    """
    A subscription plan contains the pricing information for different products and feature levels on your site.
    (Source: https://stripe.com/docs/api/python#plans)

    # = Mapping the values of this field isn't currently on our roadmap.
    Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:

    * **object** - Unnecessary. Just check the model name.

    .. attention:: Stripe API_VERSION: model fields and methods audited to 2016-03-07 - @kavdev
    """

    stripe_class = stripe.Plan
    stripe_dashboard_item_name = "plans"

    aggregate_usage = StripeEnumField(
        enum=enums.PlanAggregateUsage, stripe_required=False,
        help_text=(
            "Specifies a usage aggregation strategy for plans of usage_type=metered. "
            "Allowed values are `sum` for summing up all usage during a period, "
            "`last_during_period` for picking the last usage record reported within a "
            "period, `last_ever` for picking the last usage record ever (across period "
            "bounds) or max which picks the usage record with the maximum reported "
            "usage during a period. Defaults to `sum`."
        )
    )
    amount = StripeCurrencyField(help_text="Amount to be charged on the interval specified.")
    billing_scheme = StripeEnumField(
        enum=enums.PlanBillingScheme, stripe_required=False,
        help_text=(
            "Describes how to compute the price per period. Either `per_unit` or `tiered`. "
            "`per_unit` indicates that the fixed amount (specified in amount) will be charged "
            "per unit in quantity (for plans with `usage_type=licensed`), or per unit of total "
            "usage (for plans with `usage_type=metered`). "
            "`tiered` indicates that the unit pricing will be computed using a tiering strategy "
            "as defined using the tiers and tiers_mode attributes."
        )
    )
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code")
    interval = StripeEnumField(enum=enums.PlanInterval, help_text=(
        "The frequency with which a subscription should be billed."
    ))
    interval_count = StripeIntegerField(null=True, help_text=(
        "The number of intervals (specified in the interval property) between each subscription billing."
    ))
    nickname = StripeCharField(
        max_length=5000, stripe_required=False, help_text="A brief description of the plan, hidden from customers."
    )
    product = ForeignKey("Product", on_delete=models.SET_NULL, null=True, help_text=(
        "The product whose pricing this plan determines."
    ))
    tiers = StripeJSONField(stripe_required=False, help_text=(
        "Each element represents a pricing tier. "
        "This parameter requires `billing_scheme` to be set to `tiered`."
    ))
    tiers_mode = StripeEnumField(enum=enums.PlanTiersMode, stripe_required=False, help_text=(
        "Defines if the tiering price should be `graduated` or `volume` based. "
        "In `volume`-based tiering, the maximum quantity within a period "
        "determines the per unit price, in `graduated` tiering pricing can "
        "successively change as the quantity grows."
    ))
    transform_usage = StripeJSONField(stripe_required=False, help_text=(
        "Apply a transformation to the reported usage or set quantity "
        "before computing the billed price. Cannot be combined with `tiers`."
    ))
    trial_period_days = StripeIntegerField(null=True, help_text=(
        "Number of trial period days granted when subscribing a customer to this plan. "
        "Null if the plan has no trial period."
    ))
    usage_type = StripeEnumField(
        enum=enums.PlanUsageType, default=enums.PlanUsageType.licensed,
        help_text=(
            "Configures how the quantity per period should be determined, can be either"
            "`metered` or `licensed`. `licensed` will automatically bill the `quantity` "
            "set for a plan when adding it to a subscription, `metered` will aggregate "
            "the total usage based on usage records. Defaults to `licensed`."
        )
    )

    # Legacy fields (pre 2017-08-15)
    name = StripeTextField(
        stripe_required=False,
        help_text="Name of the plan, to be displayed on invoices and in the web interface."
    )
    statement_descriptor = StripeCharField(max_length=22, stripe_required=False, help_text=(
        "An arbitrary string to be displayed on your customer's credit card statement. The statement "
        "description may not include <>\"' characters, and will appear on your customer's statement in capital "
        "letters. Non-ASCII characters are automatically stripped. While most banks display this information "
        "consistently, some may display it incorrectly or not at all."
    ))

    class Meta(object):
        ordering = ["amount"]

    @classmethod
    def _stripe_object_to_product(cls, target_cls, data):
        """
        Search the given manager for the Product matching this Plan object's ``product`` field.

        :param target_cls: The target class
        :type target_cls: Product
        :param data: stripe object
        :type data: dict
        """

        if "product" in data and data["product"]:
            return target_cls._get_or_create_from_stripe_object(data, "product")[0]

    @classmethod
    def get_or_create(cls, **kwargs):
        """ Get or create a Plan."""

        try:
            return Plan.objects.get(stripe_id=kwargs['stripe_id']), False
        except Plan.DoesNotExist:
            return cls.create(**kwargs), True

    @classmethod
    def create(cls, **kwargs):
        # A few minor things are changed in the api-version of the create call
        api_kwargs = dict(kwargs)
        api_kwargs['id'] = api_kwargs['stripe_id']
        del(api_kwargs['stripe_id'])
        api_kwargs['amount'] = int(api_kwargs['amount'] * 100)
        cls._api_create(**api_kwargs)

        plan = Plan.objects.create(**kwargs)

        return plan

    def __str__(self):
        return self.name or self.nickname or self.stripe_id

    def _attach_objects_hook(self, cls, data):
        product = cls._stripe_object_to_product(target_cls=Product, data=data)
        if product:
            self.product = product

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        data = super(Plan, cls)._manipulate_stripe_object_hook(data)
        # Amount can be null if tiered plan
        # Set to 0 to maintain compatibility while avoiding a database
        # migration on the stable branch
        if not data['amount']:
            data['amount'] = 0
        return data

    @property
    def amount_in_cents(self):
        return int(self.amount * 100)

    @property
    def human_readable_price(self):
        amount = get_friendly_currency_amount(self.amount, self.currency)
        interval_count = self.interval_count

        if interval_count == 1:
            interval = self.interval
            template = "{amount}/{interval}"
        else:
            interval = {"day": "days", "week": "weeks", "month": "months", "year": "years"}[self.interval]
            template = "{amount} every {interval_count} {interval}"

        return template.format(amount=amount, interval=interval, interval_count=interval_count)

    # TODO: Move this type of update to the model's save() method so it happens automatically
    # Also, block other fields from being saved.
    def update_name(self):
        """Update the name of the Plan in Stripe and in the db.

        - Assumes the object being called has the name attribute already
          reset, but has not been saved.
        - Stripe does not allow for update of any other Plan attributes besides
          name.

        """

        p = self.api_retrieve()
        p.name = self.name
        p.save()

        self.save()


@python_2_unicode_compatible
class Product(StripeObject):
    """
    https://stripe.com/docs/api#product_object
    """

    stripe_class = stripe.Product
    stripe_dashboard_item_name = "products"

    # Fields applicable to both `good` and `service`
    name = StripeCharField(max_length=5000, help_text=(
        "The product's name, meant to be displayable to the customer. "
        "Applicable to both `service` and `good` types."
    ))
    type = StripeEnumField(enum=enums.ProductType, help_text=(
        "The type of the product. The product is either of type `good`, which is "
        "eligible for use with Orders and SKUs, or `service`, which is eligible "
        "for use with Subscriptions and Plans."
    ))

    # Fields applicable to `good` only
    active = StripeNullBooleanField(help_text=(
        "Whether the product is currently available for purchase. "
        "Only applicable to products of `type=good`."
    ))
    attributes = StripeJSONField(null=True, help_text=(
        "A list of up to 5 attributes that each SKU can provide values for "
        '(e.g., `["color", "size"]`). Only applicable to products of `type=good`.'
    ))
    caption = StripeCharField(null=True, max_length=5000, help_text=(
        "A short one-line description of the product, meant to be displayable"
        "to the customer. Only applicable to products of `type=good`."
    ))
    deactivate_on = StripeJSONField(stripe_required=False, help_text=(
        "An array of connect application identifiers that cannot purchase "
        "this product. Only applicable to products of `type=good`."
    ))
    images = StripeJSONField(stripe_required=False, help_text=(
        "A list of up to 8 URLs of images for this product, meant to be "
        "displayable to the customer. Only applicable to products of `type=good`."
    ))
    package_dimensions = StripeJSONField(stripe_required=False, help_text=(
        "The dimensions of this product for shipping purposes. "
        "A SKU associated with this product can override this value by having its "
        "own `package_dimensions`. Only applicable to products of `type=good`."
    ))
    shippable = StripeNullBooleanField(stripe_required=False, help_text=(
        "Whether this product is a shipped good. "
        "Only applicable to products of `type=good`."
    ))
    url = StripeCharField(max_length=799, null=True, help_text=(
        "A URL of a publicly-accessible webpage for this product. "
        "Only applicable to products of `type=good`."
    ))

    # Fields available to `service` only
    statement_descriptor = StripeCharField(stripe_required=False, max_length=22, help_text=(
        "Extra information about a product which will appear on your customer's "
        "credit card statement. In the case that multiple products are billed at "
        "once, the first statement descriptor will be used. "
        "Only available on products of type=`service`."
    ))
    unit_label = StripeCharField(stripe_required=False, max_length=12)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Subscription(StripeObject):
    """
    Subscriptions allow you to charge a customer's card on a recurring basis. A subscription ties a
    customer to a particular plan you've created.

    A subscription still in its trial period is ``trialing`` and moves to ``active`` when the trial period is over.
    When payment to renew the subscription fails, the subscription becomes ``past_due``. After Stripe has exhausted
    all payment retry attempts, the subscription ends up with a status of either ``canceled`` or ``unpaid`` depending
    on your retry settings. Note that when a subscription has a status of ``unpaid``, no subsequent invoices will be
    attempted (invoices will be created, but then immediately automatically closed. Additionally, updating customer
    card details will not lead to Stripe retrying the latest invoice.). After receiving updated card details from a
    customer, you may choose to reopen and pay their closed invoices.
    (Source: https://stripe.com/docs/api/python#subscriptions)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:

    * **object** - Unnecessary. Just check the model name.
    * **discount** - #

    .. attention:: Stripe API_VERSION: model fields and methods audited to 2016-03-07 - @kavdev
    """

    stripe_class = stripe.Subscription
    stripe_dashboard_item_name = "subscriptions"

    application_fee_percent = StripePercentField(
        null=True, blank=True,
        help_text="A positive decimal that represents the fee percentage of the subscription invoice amount that "
        "will be transferred to the application owner's Stripe account each billing period."
    )
    billing = StripeEnumField(enum=enums.InvoiceBilling, help_text=(
        "Either `charge_automatically`, or `send_invoice`. When charging automatically, "
        "Stripe will attempt to pay this subscription at the end of the cycle using the "
        "default source attached to the customer. When sending an invoice, Stripe will "
        "email your customer an invoice with payment instructions."
    ))
    billing_cycle_anchor = StripeDateTimeField(stripe_required=False, help_text=(
        "Determines the date of the first full invoice, and, for plans with `month` or "
        "`year` intervals, the day of the month for subsequent invoices."
    ))
    cancel_at_period_end = StripeBooleanField(
        default=False,
        help_text="If the subscription has been canceled with the ``at_period_end`` flag set to true, "
        "``cancel_at_period_end`` on the subscription will be true. You can use this attribute to determine whether "
        "a subscription that has a status of active is scheduled to be canceled at the end of the current period."
    )
    canceled_at = StripeDateTimeField(
        null=True, blank=True,
        help_text="If the subscription has been canceled, the date of that cancellation. If the subscription was "
        "canceled with ``cancel_at_period_end``, canceled_at will still reflect the date of the initial cancellation "
        "request, not the end of the subscription period when the subscription is automatically moved to a canceled "
        "state."
    )
    current_period_end = StripeDateTimeField(
        help_text="End of the current period for which the subscription has been invoiced. At the end of this period, "
        "a new invoice will be created."
    )
    current_period_start = StripeDateTimeField(
        help_text="Start of the current period for which the subscription has been invoiced."
    )
    customer = ForeignKey(
        "Customer", on_delete=models.CASCADE,
        related_name="subscriptions",
        help_text="The customer associated with this subscription."
    )
    days_until_due = StripeIntegerField(blank=True, stripe_required=False, help_text=(
        "Number of days a customer has to pay invoices generated by this subscription. "
        "This value will be `null` for subscriptions where `billing=charge_automatically`."
    ))
    # TODO: discount
    ended_at = StripeDateTimeField(
        null=True, blank=True,
        help_text="If the subscription has ended (either because it was canceled or because the customer was switched "
        "to a subscription to a new plan), the date the subscription ended."
    )
    # TODO: items (SubscriptionItem)
    plan = ForeignKey(
        "Plan", on_delete=models.CASCADE,
        related_name="subscriptions",
        help_text="The plan associated with this subscription."
    )
    quantity = StripeIntegerField(help_text="The quantity applied to this subscription.")
    start = StripeDateTimeField(help_text="Date the subscription started.")
    status = StripeEnumField(
        enum=enums.SubscriptionStatus, help_text="The status of this subscription."
    )
    tax_percent = StripePercentField(
        null=True, blank=True,
        help_text="A positive decimal (with at most two decimal places) between 1 and 100. This represents the "
        "percentage of the subscription invoice subtotal that will be calculated and added as tax to the final "
        "amount each billing period."
    )
    trial_end = StripeDateTimeField(
        null=True, blank=True,
        help_text="If the subscription has a trial, the end of that trial."
    )
    trial_start = StripeDateTimeField(
        null=True, blank=True,
        help_text="If the subscription has a trial, the beginning of that trial."
    )

    objects = SubscriptionManager()

    @classmethod
    def _stripe_object_to_plan(cls, target_cls, data):
        """
        Search the given manager for the Plan matching this Charge object's ``plan`` field.
        Note that the plan field is already expanded in each request and is required.

        :param target_cls: The target class
        :type target_cls: Plan
        :param data: stripe object
        :type data: dict

        """

        return target_cls._get_or_create_from_stripe_object(data["plan"])[0]

    def __str__(self):
        return "{customer} on {plan}".format(customer=text_type(self.customer), plan=text_type(self.plan))

    def update(
        self, plan=None, application_fee_percent=None, coupon=None, prorate=djstripe_settings.PRORATION_POLICY,
        proration_date=None, metadata=None, quantity=None, tax_percent=None, trial_end=None
    ):
        """
        See `Customer.subscribe() <#djstripe.models.Customer.subscribe>`__

        :param plan: The plan to which to subscribe the customer.
        :type plan: Plan or string (plan ID)
        :param prorate: Whether or not to prorate when switching plans. Default is True.
        :type prorate: boolean
        :param proration_date: If set, the proration will be calculated as though the subscription was updated at the
                               given time. This can be used to apply exactly the same proration that was previewed
                               with upcoming invoice endpoint. It can also be used to implement custom proration
                               logic, such as prorating by day instead of by second, by providing the time that you
                               wish to use for proration calculations.
        :type proration_date: datetime

        .. note:: The default value for ``prorate`` is the DJSTRIPE_PRORATION_POLICY setting.

        .. important:: Updating a subscription by changing the plan or quantity creates a new ``Subscription`` in \
        Stripe (and dj-stripe).

        .. Notes:
        .. if you're using ``Subscription.update()`` instead of ``Subscription.update()``, ``plan`` can only \
        be a string
        """

        # Convert Plan to stripe_id
        if plan is not None and isinstance(plan, Plan):
            plan = plan.stripe_id

        kwargs = deepcopy(locals())
        del kwargs["self"]

        stripe_subscription = self.api_retrieve()

        for kwarg, value in kwargs.items():
            if value is not None:
                setattr(stripe_subscription, kwarg, value)

        return Subscription.sync_from_stripe_data(stripe_subscription.save())

    def extend(self, delta):
        """
        Extends this subscription by the provided delta.

        :param delta: The timedelta by which to extend this subscription.
        :type delta: timedelta
        """

        if delta.total_seconds() < 0:
            raise ValueError("delta must be a positive timedelta.")

        if self.trial_end is not None and self.trial_end > timezone.now():
            period_end = self.trial_end
        else:
            period_end = self.current_period_end

        period_end += delta

        return self.update(prorate=False, trial_end=period_end)

    def cancel(self, at_period_end=None):
        """
        Cancels this subscription. If you set the at_period_end parameter to true, the subscription will remain active
        until the end of the period, at which point it will be canceled and not renewed. By default, the subscription
        is terminated immediately. In either case, the customer will not be charged again for the subscription. Note,
        however, that any pending invoice items that you've created will still be charged for at the end of the period
        unless manually deleted. If you've set the subscription to cancel at period end, any pending prorations will
        also be left in place and collected at the end of the period, but if the subscription is set to cancel
        immediately, pending prorations will be removed.

        By default, all unpaid invoices for the customer will be closed upon subscription cancellation. We do this in
        order to prevent unexpected payment retries once the customer has canceled a subscription. However, you can
        reopen the invoices manually after subscription cancellation to have us proceed with automatic retries, or you
        could even re-attempt payment yourself on all unpaid invoices before allowing the customer to cancel the
        subscription at all.

        :param at_period_end: A flag that if set to true will delay the cancellation of the subscription until the end
                              of the current period. Default is False.
        :type at_period_end: boolean

        .. important:: If a subscription is cancelled during a trial period, the ``at_period_end`` flag will be \
        overridden to False so that the trial ends immediately and the customer's card isn't charged.
        """
        if at_period_end is None:
            at_period_end = djstripe_settings.CANCELLATION_AT_PERIOD_END

        # If plan has trial days and customer cancels before trial period ends, then end subscription now,
        #     i.e. at_period_end=False
        if self.trial_end and self.trial_end > timezone.now():
            at_period_end = False

        if at_period_end:
            stripe_subscription = self.api_retrieve()
            stripe_subscription.cancel_at_period_end = True
            stripe_subscription.save()
        else:
            try:
                stripe_subscription = self._api_delete()
            except InvalidRequestError as exc:
                if "No such subscription:" in text_type(exc):
                    # cancel() works by deleting the subscription. The object still
                    # exists in Stripe however, and can still be retrieved.
                    # If the subscription was already canceled (status=canceled),
                    # that api_retrieve() call will fail with "No such subscription".
                    # However, this may also happen if the subscription legitimately
                    # does not exist, in which case the following line will re-raise.
                    stripe_subscription = self.api_retrieve()
                else:
                    six.reraise(*sys.exc_info())

        return Subscription.sync_from_stripe_data(stripe_subscription)

    def reactivate(self):
        """
        Reactivates this subscription.

        If a customer's subscription is canceled with ``at_period_end`` set to True and it has not yet reached the end
        of the billing period, it can be reactivated. Subscriptions canceled immediately cannot be reactivated.
        (Source: https://stripe.com/docs/subscriptions/canceling-pausing)

        .. warning:: Reactivating a fully canceled Subscription will fail silently. Be sure to check the returned \
        Subscription's status.
        """
        stripe_subscription = self.api_retrieve()
        stripe_subscription.plan = self.plan.stripe_id
        stripe_subscription.cancel_at_period_end = False

        return Subscription.sync_from_stripe_data(stripe_subscription.save())

    def is_period_current(self):
        """ Returns True if this subscription's period is current, false otherwise."""

        return self.current_period_end > timezone.now() or (self.trial_end and self.trial_end > timezone.now())

    def is_status_current(self):
        """ Returns True if this subscription's status is current (active or trialing), false otherwise."""

        return self.status in ["trialing", "active"]

    def is_status_temporarily_current(self):
        """
        A status is temporarily current when the subscription is canceled with the ``at_period_end`` flag.
        The subscription is still active, but is technically canceled and we're just waiting for it to run out.

        You could use this method to give customers limited service after they've canceled. For example, a video
        on demand service could only allow customers to download their libraries  and do nothing else when their
        subscription is temporarily current.
        """

        return self.canceled_at and self.start < self.canceled_at and self.cancel_at_period_end

    def is_valid(self):
        """ Returns True if this subscription's status and period are current, false otherwise."""

        if not self.is_status_current():
            return False

        if not self.is_period_current():
            return False

        return True

    def _attach_objects_hook(self, cls, data):
        self.customer = cls._stripe_object_to_customer(target_cls=Customer, data=data)
        self.plan = cls._stripe_object_to_plan(target_cls=Plan, data=data)


# ============================================================================ #
#                                   Connect                                    #
# ============================================================================ #

@python_2_unicode_compatible
class Account(StripeObject):
    stripe_class = stripe.Account

    business_logo = ForeignKey("FileUpload", on_delete=models.SET_NULL, null=True)
    business_name = StripeCharField(max_length=255, stripe_required=False, help_text=(
        "The publicly visible name of the business"
    ))
    business_primary_color = StripeCharField(max_length=7, stripe_required=False, help_text=(
        "A CSS hex color value representing the primary branding color for this account"
    ))
    business_url = StripeCharField(max_length=200, null=True, help_text=(
        "The publicly visible website of the business"
    ))
    charges_enabled = StripeBooleanField(help_text="Whether the account can create live charges")
    country = StripeCharField(max_length=2, help_text="The country of the account")
    debit_negative_balances = StripeNullBooleanField(stripe_required=False, default=False, help_text=(
        "A Boolean indicating if Stripe should try to reclaim negative "
        "balances from an attached bank account."
    ))
    decline_charge_on = StripeJSONField(stripe_required=False, help_text=(
        "Account-level settings to automatically decline certain types "
        "of charges regardless of the decision of the card issuer"
    ))
    default_currency = StripeCharField(max_length=3, help_text=(
        "The currency this account has chosen to use as the default"
    ))
    details_submitted = StripeBooleanField(help_text=(
        "Whether account details have been submitted. "
        "Standard accounts cannot receive payouts before this is true."
    ))
    display_name = StripeCharField(max_length=255, help_text=(
        "The display name for this account. "
        "This is used on the Stripe Dashboard to differentiate between accounts."
    ))
    email = StripeCharField(max_length=255, help_text="The primary user’s email address.")
    # TODO external_accounts = ...
    legal_entity = StripeJSONField(stripe_required=False, help_text=(
        "Information about the legal entity itself, including about the associated account representative"
    ))
    payout_schedule = StripeJSONField(stripe_required=False, help_text=(
        "Details on when funds from charges are available, and when they are paid out to an external account."
    ))
    payout_statement_descriptor = StripeCharField(
        max_length=255, default="", stripe_required=False,
        help_text="The text that appears on the bank account statement for payouts."
    )
    payouts_enabled = StripeBooleanField(help_text="Whether Stripe can send payouts to this account")
    product_description = StripeCharField(max_length=255, stripe_required=False, help_text=(
        "Internal-only description of the product sold or service provided by the business. "
        "It’s used by Stripe for risk and underwriting purposes."
    ))
    statement_descriptor = StripeCharField(max_length=255, default="", help_text=(
        "The default text that appears on credit card statements when a charge is made directly on the account"
    ))
    support_email = StripeCharField(max_length=255, help_text=(
        "A publicly shareable support email address for the business"
    ))
    support_phone = StripeCharField(max_length=255, help_text=(
        "A publicly shareable support phone number for the business"
    ))
    support_url = StripeCharField(max_length=200, stripe_required=False, help_text=(
        "A publicly shareable URL that provides support for this account"
    ))
    timezone = StripeCharField(max_length=50, help_text=(
        "The timezone used in the Stripe Dashboard for this account."
    ))
    type = StripeEnumField(enum=enums.AccountType, help_text="The Stripe account type.")
    tos_acceptance = StripeJSONField(stripe_required=False, help_text=(
        "Details on the acceptance of the Stripe Services Agreement"
    ))
    verification = StripeJSONField(stripe_required=False, help_text=(
        "Information on the verification state of the account, "
        "including what information is needed and by when"
    ))

    @classmethod
    def get_connected_account_from_token(cls, access_token):
        account_data = cls.stripe_class.retrieve(api_key=access_token)

        return cls._get_or_create_from_stripe_object(account_data)[0]

    @classmethod
    def get_default_account(cls):
        account_data = cls.stripe_class.retrieve(api_key=djstripe_settings.STRIPE_SECRET_KEY)

        return cls._get_or_create_from_stripe_object(account_data)[0]

    def __str__(self):
        return self.display_name or self.business_name


class Transfer(StripeObject):
    """
    When Stripe sends you money or you initiate a transfer to a bank account, debit card, or
    connected Stripe account, a transfer object will be created.
    (Source: https://stripe.com/docs/api/python#transfers)

    # = Mapping the values of this field isn't currently on our roadmap.
        Please use the stripe dashboard to check the value of this field instead.

    Fields not implemented:

    * **object** - Unnecessary. Just check the model name.
    * **application_fee** - #
    * **balance_transaction** - #
    * **reversals** - #

    .. TODO: Link destination to Card, Account, or Bank Account Models

    .. attention:: Stripe API_VERSION: model fields and methods audited to 2016-03-07 - @kavdev
    """

    stripe_class = stripe.Transfer
    expand_fields = ["balance_transaction"]
    stripe_dashboard_item_name = "transfers"

    objects = TransferManager()

    amount = StripeCurrencyField(help_text="The amount transferred")
    amount_reversed = StripeCurrencyField(
        stripe_required=False,
        help_text="The amount reversed (can be less than the amount attribute on the transfer if a partial "
        "reversal was issued)."
    )
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code.")
    destination = StripeIdField(help_text="ID of the bank account, card, or Stripe account the transfer was sent to.")
    destination_payment = StripeIdField(
        stripe_required=False,
        help_text="If the destination is a Stripe account, this will be the ID of the payment that the destination "
        "account received for the transfer."
    )
    # reversals = ...
    reversed = StripeBooleanField(
        default=False,
        help_text="Whether or not the transfer has been fully reversed. If the transfer is only partially "
        "reversed, this attribute will still be false."
    )
    source_transaction = StripeIdField(
        null=True,
        help_text="ID of the charge (or other transaction) that was used to fund the transfer. "
        "If null, the transfer was funded from the available balance."
    )
    source_type = StripeEnumField(enum=enums.LegacySourceType, help_text=(
        "The source balance from which this transfer came."
    ))
    transfer_group = StripeCharField(
        max_length=255, null=True, blank=True, stripe_required=False,
        help_text="A string that identifies this transaction as part of a group."
    )

    # DEPRECATED Fields
    date = StripeDateTimeField(
        help_text="Date the transfer is scheduled to arrive in the bank. This doesn't factor in delays like "
        "weekends or bank holidays."
    )
    destination_type = StripeCharField(
        stripe_name="type",
        max_length=14,
        blank=True, null=True, stripe_required=False,
        help_text="The type of the transfer destination."
    )
    failure_code = StripeEnumField(
        enum=enums.PayoutFailureCode,
        blank=True, null=True, stripe_required=False,
        help_text="Error code explaining reason for transfer failure if available. "
        "See https://stripe.com/docs/api/python#transfer_failures."
    )
    failure_message = StripeTextField(
        blank=True, null=True, stripe_required=False,
        help_text="Message to user further explaining reason for transfer failure if available."
    )
    statement_descriptor = StripeCharField(
        max_length=22,
        null=True,
        help_text="An arbitrary string to be displayed on your customer's credit card statement. The statement "
        "description may not include <>\"' characters, and will appear on your customer's statement in capital "
        "letters. Non-ASCII characters are automatically stripped. While most banks display this information "
        "consistently, some may display it incorrectly or not at all."
    )
    status = StripeEnumField(
        enum=enums.PayoutStatus,
        blank=True, null=True, stripe_required=False,
        help_text="The current status of the transfer. A transfer will be pending until it is submitted to the bank, "
        "at which point it becomes in_transit. It will then change to paid if the transaction goes through. "
        "If it does not go through successfully, its status will change to failed or canceled."
    )

    # Balance transaction can be null if the transfer failed
    fee = StripeCurrencyField(stripe_required=False, nested_name="balance_transaction")
    fee_details = StripeJSONField(stripe_required=False, nested_name="balance_transaction")

    def str_parts(self):
        return [
            "amount={amount}".format(amount=self.amount),
            "status={status}".format(status=self.status),
        ] + super(Transfer, self).str_parts()


# ============================================================================ #
#                             DJ-STRIPE RESOURCES                              #
# ============================================================================ #


def _get_version():
    from . import __version__

    return __version__


@python_2_unicode_compatible
class IdempotencyKey(models.Model):
    uuid = UUIDField(max_length=36, primary_key=True, editable=False, default=uuid.uuid4)
    action = CharField(max_length=100)
    livemode = BooleanField(help_text="Whether the key was used in live or test mode.")
    created = DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("action", "livemode")

    def __str__(self):
        return text_type(self.uuid)

    @property
    def is_expired(self):
        return timezone.now() > self.created + timedelta(hours=24)


class WebhookEventTrigger(models.Model):
    """
    An instance of a request that reached the server endpoint for Stripe webhooks.

    Webhook Events are initially **UNTRUSTED**, as it is possible for any web entity to
    post any data to our webhook url. Data posted may be valid Stripe information,  garbage, or even malicious.
    The 'valid' flag in this model monitors this.
    """
    id = models.BigAutoField(primary_key=True)
    remote_ip = models.GenericIPAddressField(
        help_text="IP address of the request client."
    )
    headers = JSONField()
    body = models.TextField(blank=True)
    valid = models.BooleanField(
        default=False,
        help_text="Whether or not the webhook event has passed validation"
    )
    processed = models.BooleanField(
        default=False,
        help_text="Whether or not the webhook event has been successfully processed"
    )
    exception = models.CharField(max_length=128, blank=True)
    traceback = models.TextField(
        blank=True, help_text="Traceback if an exception was thrown during processing"
    )
    event = models.ForeignKey(
        "Event", on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Event object contained in the (valid) Webhook"
    )
    djstripe_version = models.CharField(
        max_length=32,
        default=_get_version,  # Needs to be a callable, otherwise it's a db default.
        help_text="The version of dj-stripe when the webhook was received"
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    @classmethod
    def from_request(cls, request):
        """
        Create, validate and process a WebhookEventTrigger given a Django
        request object.

        The process is three-fold:
        1. Create a WebhookEventTrigger object from a Django request.
        2. Validate the WebhookEventTrigger as a Stripe event using the API.
        3. If valid, process it into an Event object (and child resource).
        """
        from traceback import format_exc
        from .utils import fix_django_headers

        headers = fix_django_headers(request.META)
        assert headers
        try:
            body = request.body.decode(request.encoding or "utf-8")
        except Exception:
            body = "(error decoding body)"

        ip = request.META["REMOTE_ADDR"]
        obj = cls.objects.create(headers=headers, body=body, remote_ip=ip)

        try:
            obj.valid = obj.validate()
            if obj.valid:
                if djstripe_settings.WEBHOOK_EVENT_CALLBACK:
                    # If WEBHOOK_EVENT_CALLBACK, pass it for processing
                    djstripe_settings.WEBHOOK_EVENT_CALLBACK(obj)
                else:
                    # Process the item (do not save it, it'll get saved below)
                    obj.process(save=False)
        except Exception as e:
            max_length = WebhookEventTrigger._meta.get_field("exception").max_length
            obj.exception = text_type(e)[:max_length]
            obj.traceback = format_exc()

            # Send the exception as the webhook_processing_error signal
            webhook_processing_error.send(
                sender=WebhookEventTrigger, exception=e, data=getattr(e, "http_body", "")
            )
        finally:
            obj.save()

        return obj

    @cached_property
    def json_body(self):
        import json

        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    @property
    def is_test_event(self):
        return self.json_body.get("id") == webhooks.TEST_EVENT_ID

    def validate(self, api_key=None):
        """
        The original contents of the Event message must be confirmed by
        refetching it and comparing the fetched data with the original data.

        This function makes an API call to Stripe to redownload the Event data
        and returns whether or not it matches the WebhookEventTrigger data.
        """

        local_data = self.json_body
        if "id" not in local_data or "livemode" not in local_data:
            return False

        if self.is_test_event:
            logger.info("Test webhook received: {}".format(local_data))
            return False

        livemode = local_data["livemode"]
        api_key = api_key or djstripe_settings.get_default_api_key(livemode)

        # Retrieve the event using the api_version specified in itself
        with stripe_temporary_api_version(local_data["api_version"], validate=False):
            remote_data = Event.stripe_class.retrieve(id=local_data["id"], api_key=api_key)

        return local_data["data"] == remote_data["data"]

    def process(self, save=True):
        # Reset traceback and exception in case of reprocessing
        self.exception = ""
        self.traceback = ""

        self.event = Event.process(self.json_body)
        self.processed = True
        if save:
            self.save()

        return self.event
