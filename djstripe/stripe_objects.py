# -*- coding: utf-8 -*-
"""
.. module:: djstripe.stripe_objects
   :synopsis: dj-stripe - Abstract model definitions to provide our view of Stripe's objects

.. moduleauthor:: Bill Huneke (@wahuneke)
.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

This module is an effort to isolate (as much as possible) the API dependent code in one
place. Primarily this is:

1) create models containing the fields that we care about, mapping to Stripe's fields
2) create methods for consistently syncing our database with Stripe's version of the objects
3) centralized methods for creating new database records to match incoming Stripe objects

This module defines abstract models which are then extended in models.py to provide the remaining
dj-stripe functionality.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from copy import deepcopy
import decimal
import sys

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import dateformat, six, timezone
from django.utils.encoding import python_2_unicode_compatible, smart_text
from polymorphic.models import PolymorphicModel
import stripe
from stripe.error import InvalidRequestError

from . import enums, settings as djstripe_settings
from .context_managers import stripe_temporary_api_version
from .exceptions import StripeObjectManipulationException
from .fields import (
    StripeBooleanField, StripeCharField, StripeCurrencyField, StripeDateTimeField,
    StripeFieldMixin, StripeIdField, StripeIntegerField, StripeJSONField,
    StripeNullBooleanField, StripePercentField, StripePositiveIntegerField,
    StripeTextField
)
from .managers import StripeObjectManager


# Override the default API version used by the Stripe library.
djstripe_settings.set_stripe_api_version()


# ============================================================================ #
#                           Stripe Object Base                                 #
# ============================================================================ #


@python_2_unicode_compatible
class StripeObject(models.Model):
    # This must be defined in descendants of this model/mixin
    # e.g. Event, Charge, Customer, etc.
    stripe_class = None
    expand_fields = None
    stripe_dashboard_item_name = ""

    objects = models.Manager()
    stripe_objects = StripeObjectManager()

    stripe_id = StripeIdField(unique=True, stripe_name='id')
    livemode = StripeNullBooleanField(
        default=None,
        null=True,
        stripe_required=False,
        help_text="Null here indicates that the livemode status is unknown or was previously unrecorded. Otherwise, "
        "this field indicates whether this record comes from Stripe test mode or live mode operation."
    )
    stripe_timestamp = StripeDateTimeField(
        null=True,
        stripe_required=False,
        stripe_name="created",
        help_text="The datetime this object was created in stripe."
    )
    metadata = StripeJSONField(
        blank=True,
        stripe_required=False,
        help_text="A set of key/value pairs that you can attach to an object. It can be useful for storing additional "
        "information about an object in a structured format."
    )
    description = StripeTextField(blank=True, stripe_required=False, help_text="A description of this object.")

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

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
        if self.livemode is None:
            # Livemode is unknown. Use the default secret key.
            return djstripe_settings.STRIPE_SECRET_KEY
        elif self.livemode:
            # Livemode is true, use the live secret key
            return djstripe_settings.LIVE_API_KEY or djstripe_settings.STRIPE_SECRET_KEY
        else:
            # Livemode is false, use the test secret key
            return djstripe_settings.TEST_API_KEY or djstripe_settings.STRIPE_SECRET_KEY

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
            instance.save()

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

        return cls._create_from_stripe_object(data, save=save), True

    @classmethod
    def _stripe_object_to_customer(cls, target_cls, data):
        """
        Search the given manager for the Customer matching this object's ``customer`` field.

        :param target_cls: The target class
        :type target_cls: StripeCustomer
        :param data: stripe object
        :type data: dict
        """

        if "customer" in data and data["customer"]:
            return target_cls._get_or_create_from_stripe_object(data, "customer")[0]

    @classmethod
    def _stripe_object_to_transfer(cls, target_cls, data):
        """
        Search the given manager for the Transfer matching this StripeCharge object's ``transfer`` field.

        :param target_cls: The target class
        :type target_cls: StripeTransfer
        :param data: stripe object
        :type data: dict
        """

        if "transfer" in data and data["transfer"]:
            return target_cls._get_or_create_from_stripe_object(data, "transfer")[0]

    @classmethod
    def _stripe_object_to_source(cls, target_cls, data):
        """
        Search the given manager for the source matching this object's ``source`` field.
        Note that the source field is already expanded in each request, and that it is required.

        :param target_cls: The target class
        :type target_cls: StripeSource
        :param data: stripe object
        :type data: dict
        """

        return target_cls._get_or_create_from_stripe_object(data["source"])[0]

    @classmethod
    def _stripe_object_to_invoice(cls, target_cls, data):
        """
        Search the given manager for the Invoice matching this StripeCharge object's ``invoice`` field.
        Note that the invoice field is required.

        :param target_cls: The target class
        :type target_cls: StripeInvoice
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
        :type target_cls: ``StripeInvoiceItem``
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
        :type target_cls: StripeSubscription
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


class StripeSource(PolymorphicModel, StripeObject):
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE, related_name="sources")


# ============================================================================ #
#                               Core Resources                                 #
# ============================================================================ #

class StripeCharge(StripeObject):
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
* **dispute** - #; Mapped to a ``disputed`` boolean.
* **order** - #
* **refunds** - #
* **source_transfer** - #

.. attention:: Stripe API_VERSION: model fields and methods audited to 2016-03-07 - @kavdev
    """

    class Meta:
        abstract = True

    stripe_class = stripe.Charge
    expand_fields = ["balance_transaction"]
    stripe_dashboard_item_name = "payments"

    amount = StripeCurrencyField(help_text="Amount charged.")
    amount_refunded = StripeCurrencyField(
        help_text="Amount refunded (can be less than the amount attribute on the charge "
        "if a partial refund was issued)."
    )
    captured = StripeBooleanField(
        default=False,
        help_text="If the charge was created without capturing, this boolean represents whether or not it is still "
        "uncaptured or has since been captured."
    )
    currency = StripeCharField(
        max_length=3,
        help_text="Three-letter ISO currency code representing the currency in which the charge was made."
    )
    failure_code = StripeCharField(
        max_length=30,
        null=True,
        choices=enums.ApiErrorCode.choices,
        help_text="Error code explaining reason for charge failure if available."
    )
    failure_message = StripeTextField(
        null=True,
        help_text="Message to user further explaining reason for charge failure if available."
    )
    fraud_details = StripeJSONField(help_text="Hash with information on fraud assessments for the charge.")
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
        null=True, max_length=9,
        help_text="The transaction number that appears on email receipts sent for this charge."
    )
    refunded = StripeBooleanField(
        default=False,
        help_text="Whether or not the charge has been fully refunded. If the charge is only partially refunded, "
        "this attribute will still be false."
    )
    shipping = StripeJSONField(null=True, help_text="Shipping information for the charge")
    statement_descriptor = StripeCharField(
        max_length=22, null=True,
        help_text="An arbitrary string to be displayed on your customer's credit card statement. The statement "
        "description may not include <>\"' characters, and will appear on your customer's statement in capital "
        "letters. Non-ASCII characters are automatically stripped. While most banks display this information "
        "consistently, some may display it incorrectly or not at all."
    )
    status = StripeCharField(
        max_length=10, choices=enums.ChargeStatus.choices, help_text="The status of the payment."
    )

    # Balance transaction can be null if the charge failed
    fee = StripeCurrencyField(stripe_required=False, nested_name="balance_transaction")
    fee_details = StripeJSONField(stripe_required=False, nested_name="balance_transaction")

    # dj-stripe custom stripe fields. Don't try to send these.
    source_type = StripeCharField(
        max_length=20,
        null=True,
        choices=enums.SourceType.choices,
        stripe_name="source.object",
        help_text="The payment source type. If the payment source is supported by dj-stripe, a corresponding model is "
        "attached to this Charge via a foreign key matching this field."
    )
    source_stripe_id = StripeIdField(null=True, stripe_name="source.id", help_text="The payment source id.")
    disputed = StripeBooleanField(default=False, help_text="Whether or not this charge is disputed.")
    fraudulent = StripeBooleanField(default=False, help_text="Whether or not this charge was marked as fraudulent.")

    def str_parts(self):
        return [
            "amount={amount}".format(amount=self.amount),
            "paid={paid}".format(paid=smart_text(self.paid)),
        ] + super(StripeCharge, self).str_parts()

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
        return charge_obj

    def capture(self):
        """
        Capture the payment of an existing, uncaptured, charge. This is the second half of the two-step payment flow,
        where first you created a charge with the capture option set to false.
        See https://stripe.com/docs/api#capture_charge
        """

        return self.api_retrieve().capture()

    @classmethod
    def _stripe_object_destination_to_account(cls, target_cls, data):
        """
        Search the given manager for the Account matching this StripeCharge object's ``destination`` field.

        :param target_cls: The target class
        :type target_cls: StripeAccount
        :param data: stripe object
        :type data: dict
        """

        if "destination" in data and data["destination"]:
            return target_cls._get_or_create_from_stripe_object(data, "destination")[0]

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        data["disputed"] = data["dispute"] is not None

        # Assessments reported by you have the key user_report and, if set,
        # possible values of safe and fraudulent. Assessments from Stripe have
        # the key stripe_report and, if set, the value fraudulent.
        data["fraudulent"] = bool(data["fraud_details"]) and list(data["fraud_details"].values())[0] == "fraudulent"

        return data


class StripeCustomer(StripeObject):
    """
Customer objects allow you to perform recurring charges and track multiple charges that are
associated with the same customer. (Source: https://stripe.com/docs/api/python#customers)

# = Mapping the values of this field isn't currently on our roadmap.
    Please use the stripe dashboard to check the value of this field instead.

Fields not implemented:

* **object** - Unnecessary. Just check the model name.
* **discount** - #

.. attention:: Stripe API_VERSION: model fields and methods audited to 2016-03-07 - @kavdev
    """

    class Meta:
        abstract = True

    stripe_class = stripe.Customer
    expand_fields = ["default_source"]
    stripe_dashboard_item_name = "customers"

    account_balance = StripeIntegerField(
        help_text=(
            "Current balance, if any, being stored on the customer’s account. "
            "If negative, the customer has credit to apply to the next invoice. "
            "If positive, the customer has an amount owed that will be added to the"
            "next invoice. The balance does not refer to any unpaid invoices; it "
            "solely takes into account amounts that have yet to be successfully"
            "applied to any invoice. This balance is only taken into account for "
            "recurring billing purposes (i.e., subscriptions, invoices, invoice items)."
        )
    )
    business_vat_id = StripeCharField(
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
    delinquent = StripeBooleanField(
        help_text="Whether or not the latest charge for the customer's latest invoice has failed."
    )
    email = StripeTextField(null=True)
    shipping = StripeJSONField(null=True, help_text="Shipping information associated with the customer.")

    def subscribe(self, plan, application_fee_percent=None, coupon=None, quantity=None, metadata=None,
                  tax_percent=None, trial_end=None):
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

        .. Notes:
        .. ``charge_immediately`` is only available on ``Customer.subscribe()``
        .. if you're using ``StripeCustomer.subscribe()`` instead of ``Customer.subscribe()``, ``plan`` \
        can only be a string
        """

        stripe_subscription = StripeSubscription._api_create(
            plan=plan,
            customer=self.stripe_id,
            application_fee_percent=application_fee_percent,
            coupon=coupon,
            quantity=quantity,
            metadata=metadata,
            tax_percent=tax_percent,
            trial_end=trial_end,
        )

        return stripe_subscription

    def charge(self, amount, currency, application_fee=None, capture=None, description=None, destination=None,
               metadata=None, shipping=None, source=None, statement_descriptor=None):
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
        :type source: string, StripeSource
        :param statement_descriptor: An arbitrary string to be displayed on the customer's credit card statement.
        :type statement_descriptor: string
        """

        if not isinstance(amount, decimal.Decimal):
            raise ValueError("You must supply a decimal value representing dollars.")

        # Convert StripeSource to stripe_id
        if source and isinstance(source, StripeSource):
            source = source.stripe_id

        stripe_charge = StripeCharge._api_create(
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

        return stripe_charge

    def add_invoice_item(self, amount, currency, description=None, discountable=None, invoice=None,
                         metadata=None, subscription=None):
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
        .. if you're using ``StripeCustomer.add_invoice_item()`` instead of ``Customer.add_invoice_item()``, \
        ``invoice`` and ``subscriptions`` can only be strings
        """

        if not isinstance(amount, decimal.Decimal):
            raise ValueError("You must supply a decimal value representing dollars.")

        stripe_invoiceitem = StripeInvoiceItem._api_create(
            amount=int(amount * 100),  # Convert dollars into cents
            currency=currency,
            customer=self.stripe_id,
            description=description,
            discountable=discountable,
            invoice=invoice,
            metadata=metadata,
            subscription=subscription,
        )

        return stripe_invoiceitem

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
        stripe_card = stripe_customer.sources.create(source=source)

        if set_default:
            stripe_customer.default_source = stripe_card["id"]
            stripe_customer.save()

        return stripe_card


class StripeEvent(StripeObject):
    """
Events are POSTed to our webhook url. They provide information about a Stripe event that just happened. Events
are processed in detail by their respective models (charge events by the Charge model, etc).

Events are initially **UNTRUSTED**, as it is possible for any web entity to post any data to our webhook url. Data
posted may be valid Stripe information, garbage, or even malicious. The 'valid' flag in this model monitors this.

**API VERSIONING**

This is a tricky matter when it comes to webhooks. See the discussion here_.

.. _here: https://groups.google.com/a/lists.stripe.com/forum/#!topic/api-discuss/h5Y6gzNBZp8

In this discussion, it is noted that Webhooks are produced in one API version, which will usually be
different from the version supported by Stripe plugins (such as djstripe). The solution, described there,
is:

    1) validate the receipt of a webhook event by doing an event get using the API version of the received hook event.
    2) retrieve the referenced object (e.g. the Charge, the Customer, etc) using the plugin's supported API version.
    3) process that event using the retrieved object which will, only now, be in a format that you are certain to \
    understand

# = Mapping the values of this field isn't currently on our roadmap.
    Please use the stripe dashboard to check the value of this field instead.

Fields not implemented:

* **object** - Unnecessary. Just check the model name.
* **pending_webhooks** - Unnecessary. Use the dashboard.

.. attention:: Stripe API_VERSION: model fields and methods audited to 2016-03-07 - @kavdev
    """

    class Meta:
        abstract = True

    stripe_class = stripe.Event
    stripe_dashboard_item_name = "events"

    type = StripeCharField(max_length=250, help_text="Stripe's event description code")
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
    received_api_version = StripeCharField(
        max_length=15, blank=True, stripe_name="api_version", help_text="the API version at which the event data was "
        "rendered. Blank for old entries only, all new entries will have this value"
    )
    webhook_message = StripeJSONField(
        stripe_name="data",
        help_text="data received at webhook. data should be considered to be garbage until validity check is run "
        "and valid flag is set"
    )

    def str_parts(self):
        return [
            "type={type}".format(type=self.type),
        ] + super(StripeEvent, self).str_parts()

    def api_retrieve(self, api_key=None):
        # OVERRIDING the parent version of this function
        # Event retrieve is special. For Event we don't retrieve using djstripe's API version. We always retrieve
        # using the API version that was used to send the Event (which depends on the Stripe account holders settings
        api_key = api_key or self.default_api_key
        api_version = self.received_api_version

        # Stripe API version validation is bypassed because we assume what
        # Stripe passes us is a sane and usable value.
        with stripe_temporary_api_version(api_version, validate=False):
            stripe_event = super(StripeEvent, self).api_retrieve(api_key)

        return stripe_event


class StripePayout(StripeObject):
    class Meta:
        abstract = True

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
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code.")
    failure_code = StripeCharField(
        max_length=23,
        blank=True, null=True,
        choices=enums.PayoutFailureCode.choices,
        help_text="Error code explaining reason for transfer failure if available. "
        "See https://stripe.com/docs/api/python#transfer_failures."
    )
    failure_message = StripeTextField(
        null=True, blank=True,
        help_text="Message to user further explaining reason for payout failure if available."
    )
    method = StripeCharField(
        max_length=8,
        choices=enums.PayoutMethod.choices,
        help_text=(
            "The method used to send this payout. "
            "`instant` is only supported for payouts to debit cards."
        )
    )
    statement_descriptor = StripeCharField(
        max_length=255, null=True, blank=True,
        help_text="Extra information about a payout to be displayed on the user’s bank statement."
    )
    status = StripeCharField(
        max_length=10,
        choices=enums.PayoutStatus.choices,
        help_text=(
            "Current status of the payout. "
            "A payout will be `pending` until it is submitted to the bank, at which point it "
            "becomes `in_transit`. I t will then change to paid if the transaction goes through. "
            "If it does not go through successfully, its status will change to `failed` or `canceled`."
        )
    )
    type = StripeCharField(max_length=12, choices=enums.PayoutType.choices)


class StripeTransfer(StripeObject):
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

    class Meta:
        abstract = True

    stripe_class = stripe.Transfer
    expand_fields = ["balance_transaction"]
    stripe_dashboard_item_name = "transfers"

    # The following accessors are deprecated as of 1.0 and will be removed in 1.1
    # Please use enums.SubscriptionStatus directly.
    STATUS_PAID = enums.PayoutStatus.paid
    STATUS_PENDING = enums.PayoutStatus.pending
    STATUS_IN_TRANSIT = enums.PayoutStatus.in_transit
    STATUS_CANCELED = enums.PayoutStatus.canceled
    STATUS_CANCELLED = STATUS_CANCELED
    STATUS_FAILED = enums.PayoutStatus.failed

    DESTINATION_TYPES = ["card", "bank_account", "stripe_account"]
    DESITNATION_TYPE_CHOICES = [
        (destination_type, destination_type.replace("_", " ").title()) for destination_type in DESTINATION_TYPES
    ]

    amount = StripeCurrencyField(help_text="The amount transferred")
    amount_reversed = StripeCurrencyField(
        stripe_required=False,
        help_text="The amount reversed (can be less than the amount attribute on the transfer if a partial "
        "reversal was issued)."
    )
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code.")
    date = StripeDateTimeField(
        help_text="Date the transfer is scheduled to arrive in the bank. This doesn't factor in delays like "
        "weekends or bank holidays."
    )
    destination = StripeIdField(help_text="ID of the bank account, card, or Stripe account the transfer was sent to.")
    destination_payment = StripeIdField(
        stripe_required=False,
        help_text="If the destination is a Stripe account, this will be the ID of the payment that the destination "
        "account received for the transfer."
    )
    destination_type = StripeCharField(
        stripe_name="type",
        max_length=14,
        choices=DESITNATION_TYPE_CHOICES,
        blank=True, null=True, stripe_required=False,
        help_text="The type of the transfer destination."
    )
    failure_code = StripeCharField(
        max_length=23,
        blank=True, null=True, stripe_required=False,
        choices=enums.PayoutFailureCode.choices,
        help_text="Error code explaining reason for transfer failure if available. "
        "See https://stripe.com/docs/api/python#transfer_failures."
    )
    failure_message = StripeTextField(
        blank=True, null=True, stripe_required=False,
        help_text="Message to user further explaining reason for transfer failure if available."
    )
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
    source_type = StripeCharField(
        max_length=16,
        choices=enums.SourceType.choices,
        help_text="The source balance from which this transfer came."
    )
    statement_descriptor = StripeCharField(
        max_length=22,
        null=True,
        help_text="An arbitrary string to be displayed on your customer's credit card statement. The statement "
        "description may not include <>\"' characters, and will appear on your customer's statement in capital "
        "letters. Non-ASCII characters are automatically stripped. While most banks display this information "
        "consistently, some may display it incorrectly or not at all."
    )
    status = StripeCharField(
        max_length=10,
        choices=enums.PayoutStatus.choices,
        blank=True, null=True, stripe_required=False,
        help_text="The current status of the transfer. A transfer will be pending until it is submitted to the bank, "
        "at which point it becomes in_transit. It will then change to paid if the transaction goes through. "
        "If it does not go through successfully, its status will change to failed or canceled."
    )

    # Balance transaction can be null if the transfer failed
    fee = StripeCurrencyField(stripe_required=False, nested_name="balance_transaction")
    fee_details = StripeJSONField(stripe_required=False, nested_name="balance_transaction")

    # DEPRECATED Fields
    adjustment_count = StripeIntegerField(deprecated=True)
    adjustment_fees = StripeCurrencyField(deprecated=True)
    adjustment_gross = StripeCurrencyField(deprecated=True)
    charge_count = StripeIntegerField(deprecated=True)
    charge_fees = StripeCurrencyField(deprecated=True)
    charge_gross = StripeCurrencyField(deprecated=True)
    collected_fee_count = StripeIntegerField(deprecated=True)
    collected_fee_gross = StripeCurrencyField(deprecated=True)
    net = StripeCurrencyField(deprecated=True)
    refund_count = StripeIntegerField(deprecated=True)
    refund_fees = StripeCurrencyField(deprecated=True)
    refund_gross = StripeCurrencyField(deprecated=True)
    validation_count = StripeIntegerField(deprecated=True)
    validation_fees = StripeCurrencyField(deprecated=True)

    def str_parts(self):
        return [
            "amount={amount}".format(amount=self.amount),
            "status={status}".format(status=self.status),
        ] + super(StripeTransfer, self).str_parts()


# ============================================================================ #
#                                   Connect                                    #
# ============================================================================ #

class StripeAccount(StripeObject):

    class Meta:
        abstract = True

    stripe_class = stripe.Account

    # Account -- add_card(external_account);

    @classmethod
    def get_connected_account_from_token(cls, access_token):
        account_data = cls.stripe_class.retrieve(api_key=access_token)

        return cls._get_or_create_from_stripe_object(account_data)[0]

    @classmethod
    def get_default_account(cls):
        account_data = cls.stripe_class.retrieve(api_key=djstripe_settings.STRIPE_SECRET_KEY)

        return cls._get_or_create_from_stripe_object(account_data)[0]


# ============================================================================ #
#                               Payment Methods                                #
# ============================================================================ #

class StripeCard(StripeSource):
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

    class Meta:
        abstract = True

    stripe_class = stripe.Card

    address_city = StripeTextField(null=True, help_text="Billing address city.")
    address_country = StripeTextField(null=True, help_text="Billing address country.")
    address_line1 = StripeTextField(null=True, help_text="Billing address (Line 1).")
    address_line1_check = StripeCharField(
        null=True,
        max_length=11,
        choices=enums.CardCheckResult.choices,
        help_text="If ``address_line1`` was provided, results of the check."
    )
    address_line2 = StripeTextField(null=True, help_text="Billing address (Line 2).")
    address_state = StripeTextField(null=True, help_text="Billing address state.")
    address_zip = StripeTextField(null=True, help_text="Billing address zip code.")
    address_zip_check = StripeCharField(
        null=True,
        max_length=11,
        choices=enums.CardCheckResult.choices,
        help_text="If ``address_zip`` was provided, results of the check."
    )
    brand = StripeCharField(max_length=16, choices=enums.CardBrand.choices, help_text="Card brand.")
    country = StripeCharField(max_length=2, help_text="Two-letter ISO code representing the country of the card.")
    cvc_check = StripeCharField(
        null=True,
        max_length=11,
        choices=enums.CardCheckResult.choices,
        help_text="If a CVC was provided, results of the check."
    )
    dynamic_last4 = StripeCharField(
        null=True,
        max_length=4,
        help_text="(For tokenized numbers only.) The last four digits of the device account number."
    )
    exp_month = StripeIntegerField(help_text="Card expiration month.")
    exp_year = StripeIntegerField(help_text="Card expiration year.")
    fingerprint = StripeTextField(stripe_required=False, help_text="Uniquely identifies this particular card number.")
    funding = StripeCharField(
        max_length=7, choices=enums.CardFundingType.choices, help_text="Card funding type."
    )
    last4 = StripeCharField(max_length=4, help_text="Last four digits of Card number.")
    name = StripeTextField(null=True, help_text="Cardholder name.")
    tokenization_method = StripeCharField(
        null=True,
        max_length=11,
        choices=enums.CardTokenizationMethod.choices,
        help_text="If the card number is tokenized, this is the method that was used."
    )

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

    @staticmethod
    def _get_customer_from_kwargs(**kwargs):
        if "customer" not in kwargs or not isinstance(kwargs["customer"], StripeCustomer):
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

    def str_parts(self):
        return [
            "brand={brand}".format(brand=self.brand),
            "last4={last4}".format(last4=self.last4),
            "exp_month={exp_month}".format(exp_month=self.exp_month),
            "exp_year={exp_year}".format(exp_year=self.exp_year),
        ] + super(StripeCard, self).str_parts()

# TODO: Coming eventually
#     @classmethod
#     def stripe_object_to_account(cls, target_cls, data):
#         """
#         Search the given manager for the Account matching this StripeCharge object's ``account`` field.
#
#         :param target_cls: The target class
#         :type target_cls: StripeAccount
#         :param data: stripe object
#         :type data: dict
#         """
#
#         if "account" in data and data["account"]:
#             return target_cls._get_or_create_from_stripe_object(data, "account")[0]

    @classmethod
    def create_token(cls, number, exp_month, exp_year, cvc, **kwargs):
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

        return stripe.Token.create(card=card)


class StripeCoupon(StripeObject):

    DURATION_FOREVER = "forever"
    DURATION_ONCE = "once"
    DURATION_REPEATING = "repeating"

    class Meta:
        abstract = True
        unique_together = ("stripe_id", "livemode")

    stripe_class = stripe.Coupon
    stripe_dashboard_item_name = "coupons"

    stripe_id = StripeIdField(stripe_name="id", max_length=500)
    amount_off = StripeCurrencyField(
        null=True, blank=True,
        help_text="Amount that will be taken off the subtotal of any invoices for this customer."
    )
    currency = StripeCharField(null=True, blank=True, max_length=3, help_text="Three-letter ISO currency code")
    duration = StripeCharField(
        max_length=9, choices=enums.CouponDuration.choices,
        help_text="Describes how long a customer who applies this coupon will get the discount."
    )
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


# ============================================================================ #
#                                Subscriptions                                 #
# ============================================================================ #

class StripeInvoice(StripeObject):
    """
Invoices are statements of what a customer owes for a particular billing period, including subscriptions,
invoice items, and any automatic proration adjustments if necessary.

Once an invoice is created, payment is automatically attempted. Note that the payment, while automatic,
does not happen exactly at the time of invoice creation. If you have configured webhooks, the invoice
will wait until one hour after the last webhook is successfully sent (or the last webhook times out after failing).

Any customer credit on the account is applied before determining how much is due for that invoice (the amount that
will be actually charged). If the amount due for the invoice is less than 50 cents (the minimum for a charge), we
add the amount to the customer's running account balance to be added to the next invoice. If this amount is negative,
it will act as a credit to offset the next invoice. Note that the customer account balance does not include unpaid
invoices; it only includes balances that need to be taken into account when calculating the amount due for the next
invoice.
(Source: https://stripe.com/docs/api/python#invoices)

# = Mapping the values of this field isn't currently on our roadmap.
    Please use the stripe dashboard to check the value of this field instead.

Fields not implemented:

* **object** - Unnecessary. Just check the model name.
* **discount** - #
* **lines** - Unnecessary. Check Subscription and InvoiceItems directly.
* **receipt_number** - Unnecessary. Use the dashboard. Create a feature request if this is functionality you need.
* **webhooks_delivered_at** - Unnecessary. Create a feature request if this is functionality you need.

.. attention:: Stripe API_VERSION: model fields and methods audited to 2016-03-07 - @kavdev
    """

    class Meta:
        abstract = True

    stripe_class = stripe.Invoice
    stripe_dashboard_item_name = "invoices"

    amount_due = StripeCurrencyField(
        help_text="Final amount due at this time for this invoice. If the invoice's total is smaller than the minimum "
        "charge amount, for example, or if there is account credit that can be applied to the invoice, the amount_due "
        "may be 0. If there is a positive starting_balance for the invoice (the customer owes money), the amount_due "
        "will also take that into account. The charge that gets generated for the invoice will be for the amount "
        "specified in amount_due."
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
    closed = StripeBooleanField(
        default=False,
        help_text="Whether or not the invoice is still trying to collect payment. An invoice is closed if it's either "
        "paid or it has been marked closed. A closed invoice will no longer attempt to collect payment."
    )
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code.")
    date = StripeDateTimeField(help_text="The date on the invoice.")
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
    next_payment_attempt = StripeDateTimeField(
        null=True,
        help_text="The time at which payment will next be attempted."
    )
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

    def str_parts(self):
        return [
            "amount_due={amount_due}".format(amount_due=self.amount_due),
            "date={date}".format(date=self.date),
            "status={status}".format(status=self.status),
        ] + super(StripeInvoice, self).str_parts()

    @classmethod
    def _stripe_object_to_charge(cls, target_cls, data):
        """
        Search the given manager for the Charge matching this object's ``charge`` field.

        :param target_cls: The target class
        :type target_cls: StripeCharge
        :param data: stripe object
        :type data: dict
        """

        if "charge" in data and data["charge"]:
            return target_cls._get_or_create_from_stripe_object(data, "charge")[0]

    @classmethod
    def upcoming(cls, api_key=djstripe_settings.STRIPE_SECRET_KEY, customer=None, coupon=None, subscription=None,
                 subscription_plan=None, subscription_prorate=None, subscription_proration_date=None,
                 subscription_quantity=None, subscription_trial_end=None, **kwargs):
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
            if str(exc) != "Nothing to invoice for customer":
                six.reraise(*sys.exc_info())
            return

        # Workaround for "id" being missing (upcoming invoices don't persist).
        upcoming_stripe_invoice["id"] = "upcoming"

        return upcoming_stripe_invoice

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


class StripeInvoiceItem(StripeObject):
    """
Sometimes you want to add a charge or credit to a customer but only actually charge the customer's
card at the end of a regular billing cycle. This is useful for combining several charges to
minimize per-transaction fees or having Stripe tabulate your usage-based billing totals.
(Source: https://stripe.com/docs/api/python#invoiceitems)

# = Mapping the values of this field isn't currently on our roadmap.
    Please use the stripe dashboard to check the value of this field instead.

Fields not implemented:

* **object** - Unnecessary. Just check the model name.

.. attention:: Stripe API_VERSION: model fields and methods audited to 2016-03-07 - @kavdev
    """

    class Meta:
        abstract = True

    stripe_class = stripe.InvoiceItem

    amount = StripeCurrencyField(help_text="Amount invoiced.")
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code.")
    date = StripeDateTimeField(help_text="The date on the invoiceitem.")
    discountable = StripeBooleanField(
        default=False,
        help_text="If True, discounts will apply to this invoice item. Always False for prorations."
    )
    period_end = StripeDateTimeField(
        stripe_name="period.end",
        help_text="Might be the date when this invoiceitem's invoice was sent."
    )
    period_start = StripeDateTimeField(
        stripe_name="period.start",
        help_text="Might be the date when this invoiceitem was added to the invoice"
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

    def str_parts(self):
        return [
            "amount={amount}".format(amount=self.amount),
            "date={date}".format(date=self.date),
        ] + super(StripeInvoiceItem, self).str_parts()

    @classmethod
    def _stripe_object_to_plan(cls, target_cls, data):
        """
        Search the given manager for the Plan matching this StripeCharge object's ``plan`` field.

        :param target_cls: The target class
        :type target_cls: StripePlan
        :param data: stripe object
        :type data: dict

        """

        if "plan" in data and data["plan"]:
            return target_cls._get_or_create_from_stripe_object(data, "plan")[0]


class StripePlan(StripeObject):
    """
A subscription plan contains the pricing information for different products and feature levels on your site.
(Source: https://stripe.com/docs/api/python#plans)

# = Mapping the values of this field isn't currently on our roadmap.
    Please use the stripe dashboard to check the value of this field instead.

Fields not implemented:

* **object** - Unnecessary. Just check the model name.

.. attention:: Stripe API_VERSION: model fields and methods audited to 2016-03-07 - @kavdev
    """

    class Meta:
        abstract = True

    stripe_class = stripe.Plan
    stripe_dashboard_item_name = "plans"

    amount = StripeCurrencyField(help_text="Amount to be charged on the interval specified.")
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code")
    interval = StripeCharField(
        max_length=5,
        choices=enums.PlanInterval.choices,
        help_text="The frequency with which a subscription should be billed."
    )
    interval_count = StripeIntegerField(
        null=True,
        help_text="The number of intervals (specified in the interval property) between each subscription billing."
    )
    name = StripeTextField(help_text="Name of the plan, to be displayed on invoices and in the web interface.")
    statement_descriptor = StripeCharField(
        max_length=22,
        null=True,
        help_text="An arbitrary string to be displayed on your customer's credit card statement. The statement "
        "description may not include <>\"' characters, and will appear on your customer's statement in capital "
        "letters. Non-ASCII characters are automatically stripped. While most banks display this information "
        "consistently, some may display it incorrectly or not at all."
    )
    trial_period_days = StripeIntegerField(
        null=True,
        help_text="Number of trial period days granted when subscribing a customer to this plan. "
        "Null if the plan has no trial period."
    )

    @property
    def amount_in_cents(self):
        return int(self.amount * 100)


class StripeSubscription(StripeObject):
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

    class Meta:
        abstract = True

    stripe_class = stripe.Subscription
    stripe_dashboard_item_name = "subscriptions"

    # The following accessors are deprecated as of 1.0 and will be removed in 1.1
    # Please use enums.SubscriptionStatus directly.
    STATUS_ACTIVE = enums.SubscriptionStatus.active
    STATUS_TRIALING = enums.SubscriptionStatus.trialing
    STATUS_PAST_DUE = enums.SubscriptionStatus.past_due
    STATUS_CANCELED = enums.SubscriptionStatus.canceled
    STATUS_CANCELLED = STATUS_CANCELED
    STATUS_UNPAID = enums.SubscriptionStatus.unpaid

    application_fee_percent = StripePercentField(
        null=True,
        help_text="A positive decimal that represents the fee percentage of the subscription invoice amount that "
        "will be transferred to the application owner's Stripe account each billing period."
    )
    cancel_at_period_end = StripeBooleanField(
        default=False,
        help_text="If the subscription has been canceled with the ``at_period_end`` flag set to true, "
        "``cancel_at_period_end`` on the subscription will be true. You can use this attribute to determine whether "
        "a subscription that has a status of active is scheduled to be canceled at the end of the current period."
    )
    canceled_at = StripeDateTimeField(
        null=True,
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
    ended_at = StripeDateTimeField(
        null=True,
        help_text="If the subscription has ended (either because it was canceled or because the customer was switched "
        "to a subscription to a new plan), the date the subscription ended."
    )
    quantity = StripeIntegerField(help_text="The quantity applied to this subscription.")
    start = StripeDateTimeField(help_text="Date the subscription started.")
    status = StripeCharField(
        max_length=8, choices=enums.SubscriptionStatus.choices, help_text="The status of this subscription."
    )
    tax_percent = StripePercentField(
        null=True,
        help_text="A positive decimal (with at most two decimal places) between 1 and 100. This represents the "
        "percentage of the subscription invoice subtotal that will be calculated and added as tax to the final "
        "amount each billing period."
    )
    trial_end = StripeDateTimeField(null=True, help_text="If the subscription has a trial, the end of that trial.")
    trial_start = StripeDateTimeField(
        null=True,
        help_text="If the subscription has a trial, the beginning of that trial."
    )

    @classmethod
    def _stripe_object_to_plan(cls, target_cls, data):
        """
        Search the given manager for the Plan matching this StripeCharge object's ``plan`` field.
        Note that the plan field is already expanded in each request and is required.

        :param target_cls: The target class
        :type target_cls: StripePlan
        :param data: stripe object
        :type data: dict

        """

        return target_cls._get_or_create_from_stripe_object(data["plan"])[0]

    def update(self, plan=None, application_fee_percent=None, coupon=None, prorate=None, proration_date=None,
               metadata=None, quantity=None, tax_percent=None, trial_end=None):
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

        .. note:: The default value for ``prorate`` is overridden by the DJSTRIPE_PRORATION_POLICY setting.

        .. important:: Updating a subscription by changing the plan or quantity creates a new ``Subscription`` in \
        Stripe (and dj-stripe).

        .. Notes:
        .. if you're using ``StripeSubscription.update()`` instead of ``Subscription.update()``, ``plan`` can only \
        be a string
        """

        kwargs = deepcopy(locals())
        del kwargs["self"]

        stripe_subscription = self.api_retrieve()

        for kwarg, value in kwargs.items():
            if value is not None:
                setattr(stripe_subscription, kwarg, value)

        return stripe_subscription.save()

    def extend(self, delta):
        """
        Extends this subscription by the provided delta.

        :param delta: The timedelta by which to extend this subscription.
        :type delta: timedelta

        """

        if delta.total_seconds() < 0:
            raise ValueError("delta must be a positive timedelta.")

        period_end = None

        if self.trial_end is not None and self.trial_end > timezone.now():
            period_end = self.trial_end
        else:
            period_end = self.current_period_end

        period_end += delta

        return StripeSubscription.update(self, prorate=False, trial_end=period_end)

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

        try:
            stripe_subscription = self._api_delete(at_period_end=at_period_end)
        except InvalidRequestError as exc:
            if "No such subscription:" in str(exc):
                # cancel() works by deleting the subscription. The object still
                # exists in Stripe however, and can still be retrieved.
                # If the subscription was already canceled (status=canceled),
                # that api_retrieve() call will fail with "No such subscription".
                # However, this may also happen if the subscription legitimately
                # does not exist, in which case the following line will re-raise.
                stripe_subscription = self.api_retrieve()
            else:
                six.reraise(*sys.exc_info())

        return stripe_subscription

    def reactivate(self):
        """
        Reactivates this subscription.

        If a customer’s subscription is canceled with ``at_period_end`` set to True and it has not yet reached the end
        of the billing period, it can be reactivated. Subscriptions canceled immediately cannot be reactivated.
        (Source: https://stripe.com/docs/subscriptions/canceling-pausing)

        .. warning:: Reactivating a fully canceled Subscription will fail silently. Be sure to check the returned \
        Subscription's status.
        """
        return self.update(plan=self.plan)
