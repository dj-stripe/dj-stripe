# -*- coding: utf-8 -*-
"""
.. module:: djstripe.models
   :synopsis: dj-stripe - Django ORM model definitions

.. moduleauthor:: Daniel Greenfeld (@pydanny)
.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

"""

from __future__ import unicode_literals

import logging
import sys

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import models
from django.db.models.fields.related import ForeignKey, OneToOneField
from django.db.models.deletion import SET_NULL
from django.db.models.fields import BooleanField, DateTimeField, NullBooleanField, TextField, CharField
from django.template.loader import render_to_string
from django.utils import six, timezone
from django.utils.encoding import python_2_unicode_compatible, smart_text
from django.utils.functional import cached_property
from doc_inherit import class_doc_inherit
from mock_django.query import QuerySetMock
from model_utils.models import TimeStampedModel
from stripe.error import StripeError, InvalidRequestError

import traceback as exception_traceback

from . import settings as djstripe_settings
from . import webhooks
from .exceptions import MultipleSubscriptionException
from .managers import SubscriptionManager, ChargeManager, TransferManager
from .signals import WEBHOOK_SIGNALS
from .signals import webhook_processing_error
from .stripe_objects import (StripeSource, StripeCharge, StripeCustomer, StripeCard, StripeSubscription,
                             StripePlan, StripeInvoice, StripeInvoiceItem, StripeTransfer, StripeAccount, StripeEvent)


logger = logging.getLogger(__name__)


# ============================================================================ #
#                               Core Resources                                 #
# ============================================================================ #


@class_doc_inherit
class Charge(StripeCharge):
    __doc__ = getattr(StripeCharge, "__doc__")

    account = ForeignKey(
        "Account", on_delete=models.CASCADE, null=True,
        related_name="charges",
        help_text="The account the charge was made on behalf of. Null here indicates that this value was never set."
    )

    customer = ForeignKey(
        "Customer", on_delete=models.CASCADE,
        related_name="charges",
        help_text="The customer associated with this charge."
    )
    transfer = ForeignKey(
        "Transfer",
        null=True, on_delete=models.CASCADE,
        help_text="The transfer to the destination account (only applicable if the charge was created using the "
        "destination parameter)."
    )

    source = ForeignKey(
        StripeSource,
        null=True,
        related_name="charges",
        on_delete=SET_NULL,
        help_text="The source used for this charge."
    )

    receipt_sent = BooleanField(default=False, help_text="Whether or not a receipt was sent for this charge.")

    objects = ChargeManager()

    def refund(self, amount=None, reason=None):
        refunded_charge = super(Charge, self).refund(amount, reason)
        return Charge.sync_from_stripe_data(refunded_charge)

    def capture(self):
        captured_charge = super(Charge, self).capture()
        return Charge.sync_from_stripe_data(captured_charge)

    def send_receipt(self):
        """Send a receipt for this charge."""

        if not self.receipt_sent:
            site = Site.objects.get_current()
            protocol = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")
            ctx = {
                "charge": self,
                "site": site,
                "protocol": protocol,
            }
            subject = render_to_string("djstripe/email/subject.txt", ctx)
            subject = subject.strip()
            message = render_to_string("djstripe/email/body.txt", ctx)
            num_sent = EmailMessage(
                subject,
                message,
                to=[self.customer.subscriber.email],
                from_email=djstripe_settings.INVOICE_FROM_EMAIL
            ).send()
            self.receipt_sent = num_sent > 0
            self.save()

    def _attach_objects_hook(self, cls, data):
        customer = cls._stripe_object_to_customer(target_cls=Customer, data=data)
        if customer:
            self.customer = customer
        else:
            raise ValidationError("A customer was not attached to this charge.")

        transfer = cls._stripe_object_to_transfer(target_cls=Transfer, data=data)
        if transfer:
            self.transfer = transfer

        # Set the account on this object.
        destination_account = cls._stripe_object_destination_to_account(target_cls=Account, data=data)
        if destination_account:
            self.account = destination_account
        else:
            self.account = Account.get_default_account()

        # TODO: other sources
        if self.source_type == "card":
            self.source = cls._stripe_object_to_source(target_cls=Card, data=data)


@class_doc_inherit
class Customer(StripeCustomer):
    doc = """

.. note:: Sources and Subscriptions are attached via a ForeignKey on StripeSource and Subscription, respectively. \
Use ``Customer.sources`` and ``Customer.subscriptions`` to access them.
    """
    __doc__ = getattr(StripeCustomer, "__doc__") + doc

    # account = ForeignKey(Account, related_name="customers")

    default_source = ForeignKey(StripeSource, null=True, related_name="customers", on_delete=SET_NULL)

    subscriber = OneToOneField(djstripe_settings.get_subscriber_model_string(), null=True,
                               on_delete=SET_NULL, related_name="customer")
    date_purged = DateTimeField(null=True, editable=False)

    def str_parts(self):
        parts = []

        if self.subscriber:
            parts.append(smart_text(self.subscriber))
            parts.append("email={email}".format(email=self.subscriber.email))
        else:
            parts.append("(deleted)")

        parts.extend(super(Customer, self).str_parts())

        return parts

    @classmethod
    def get_or_create(cls, subscriber):
        """
        Get or create a dj-stripe customer.

        :param subscriber: The subscriber model instance for which to get or create a customer.
        :type subscriber: User
        """

        try:
            return Customer.objects.get(subscriber=subscriber), False
        except Customer.DoesNotExist:
            return cls.create(subscriber), True

    @classmethod
    def create(cls, subscriber):
        trial_days = None
        if djstripe_settings.trial_period_for_subscriber_callback:
            trial_days = djstripe_settings.trial_period_for_subscriber_callback(subscriber)

        stripe_customer = cls._api_create(email=subscriber.email)
        customer = Customer.objects.create(subscriber=subscriber, stripe_id=stripe_customer["id"], currency="usd")

        if djstripe_settings.DEFAULT_PLAN and trial_days:
            customer.subscribe(
                plan=djstripe_settings.DEFAULT_PLAN,
                trial_end=timezone.now() + timezone.timedelta(days=trial_days)
            )

        return customer

    def purge(self):
        try:
            self._api_delete()
        except InvalidRequestError as exc:
            if "No such customer:" in str(exc):
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

        super(Customer, self).purge()
        self.date_purged = timezone.now()
        self.save()

    # TODO: Override Queryset.delete() with a custom manager, since this doesn't get called in bulk deletes
    #       (or cascades, but that's another matter)
    def delete(self, using=None, keep_parents=False):
        """
        Overriding the delete method to keep the customer in the records. All identifying information is removed
        via the purge() method.

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
    def subscription(self):
        """
        Shortcut to get this customer's subscription.

        :returns: None if the customer has no subscriptions, the subscription if
                  the customer has a subscription.
        :raises MultipleSubscriptionException: Raised if the customer has multiple subscriptions.
                In this case, use ``Customer.subscriptions`` instead.
        """

        subscription_count = self.subscriptions.count()

        if subscription_count == 0:
            return None
        elif subscription_count == 1:
            return self.subscriptions.first()
        else:
            raise MultipleSubscriptionException("This customer has multiple subscriptions. Use Customer.subscriptions "
                                                "to access them.")

    # TODO: Accept a coupon object when coupons are implemented
    def subscribe(self, plan, charge_immediately=True, **kwargs):
        # Convert Plan to stripe_id
        if isinstance(plan, Plan):
            plan = plan.stripe_id

        stripe_subscription = super(Customer, self).subscribe(plan=plan, **kwargs)

        if charge_immediately:
            self.send_invoice()

        return Subscription.sync_from_stripe_data(stripe_subscription)

    def can_charge(self):
        """Determines if this customer is able to be charged."""

        return self.has_valid_source() and self.date_purged is None

    def charge(self, amount, currency="usd", send_receipt=None, **kwargs):
        if send_receipt is None:
            send_receipt = getattr(settings, 'DJSTRIPE_SEND_INVOICE_RECEIPT_EMAILS', True)

        stripe_charge = super(Customer, self).charge(amount=amount, currency=currency, **kwargs)
        charge = Charge.sync_from_stripe_data(stripe_charge)

        if send_receipt:
            charge.send_receipt()

        return charge

    def add_invoice_item(self, amount, currency, **kwargs):
        # Convert Invoice to stripe_id
        if "invoice" in kwargs and isinstance(kwargs["invoice"], Invoice):
            kwargs.update({"invoice": kwargs["invoice"].stripe_id})

        # Convert Subscription to stripe_id
        if "subscription" in kwargs and isinstance(kwargs["subscription"], Subscription):
            kwargs.update({"subscription": kwargs["subscription"].stripe_id})

        stripe_invoiceitem = super(Customer, self).add_invoice_item(amount=amount, currency=currency, **kwargs)

        return InvoiceItem.sync_from_stripe_data(stripe_invoiceitem)

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
                if str(exc) != "Invoice is already paid":
                    six.reraise(*sys.exc_info())

    def has_valid_source(self):
        """ Check whether the customer has a valid payment source."""
        return self.default_source is not None

    def add_card(self, source, set_default=True):
        new_stripe_card = super(Customer, self).add_card(source, set_default)
        new_card = Card.sync_from_stripe_data(new_stripe_card)

        # Change the default source
        if set_default:
            self.default_source = new_card
            self.save()

        return new_card

    def upcoming_invoice(self, **kwargs):
        """ Gets the upcoming preview invoice (singular) for this customer.

        See `Invoice.upcoming() <#djstripe.Invoice.upcoming>`__.

        The ``customer`` argument to the ``upcoming()`` call is automatically set by this method.
        """

        kwargs['customer'] = self
        return Invoice.upcoming(**kwargs)

    def _attach_objects_hook(self, cls, data):
        # TODO: other sources
        if data["default_source"] and data["default_source"]["object"] == "card":
            self.default_source = cls._stripe_object_default_source_to_source(target_cls=Card, data=data)

    # SYNC methods should be dropped in favor of the master sync infrastructure proposed
    def _sync_invoices(self, **kwargs):
        for stripe_invoice in Invoice.api_list(customer=self.stripe_id, **kwargs):
            Invoice.sync_from_stripe_data(stripe_invoice)

    def _sync_charges(self, **kwargs):
        for stripe_charge in Charge.api_list(customer=self.stripe_id, **kwargs):
            Charge.sync_from_stripe_data(stripe_charge)

    def _sync_subscriptions(self, **kwargs):
        for stripe_subscription in Subscription.api_list(customer=self.stripe_id, **kwargs):
            Subscription.sync_from_stripe_data(stripe_subscription)


@class_doc_inherit
class Event(StripeEvent):
    __doc__ = getattr(StripeEvent, "__doc__")

    # account = ForeignKey(Account, related_name="events")

    customer = ForeignKey(
        "Customer",
        null=True, on_delete=models.CASCADE,
        help_text="In the event that there is a related customer, this will point to that Customer record"
    )
    valid = NullBooleanField(
        null=True,
        help_text="Tri-state bool. Null == validity not yet confirmed. Otherwise, this field indicates that this "
        "event was checked via stripe api and found to be either authentic (valid=True) or in-authentic (possibly "
        "malicious)"
    )

    processed = BooleanField(
        default=False,
        help_text="If validity is performed, webhook event processor(s) may run to take further action on the event. "
        "Once these have run, this is set to True."
    )

    @property
    def message(self):
        """ The event's data if the event is valid, None otherwise."""

        return self.webhook_message if self.valid else None

    def validate(self):
        """
        The original contents of the Event message comes from a POST to the webhook endpoint. This data
        must be confirmed by re-fetching it and comparing the fetched data with the original data. That's what
        this function does.

        This function makes an API call to Stripe to re-download the Event data. It then
        marks this record's valid flag to True or False.
        """

        self.valid = self.webhook_message == self.api_retrieve()["data"]
        self.save()

    def process(self, force=False, raise_exception=False):
        """
        Invokes any webhook handlers that have been registered for this event
        based on event type or event sub-type.

        See event handlers registered in the ``djstripe.event_handlers`` module
        (or handlers registered in djstripe plugins or contrib packages).

        :param force: If True, force the event to be processed by webhook
        handlers, even if the event has already been processed previously.
        :type force: bool
        :param raise_exception: If True, any Stripe errors raised during
        processing will be raised to the caller after logging the exception.
        :type raise_exception: bool
        :returns: True if the webhook was processed successfully or was
        previously processed successfully.
        :rtype: bool
        """

        if not self.valid:
            return False

        if not self.processed or force:
            exc_value = None

            try:
                # TODO: would it make sense to wrap the next 4 lines in a transaction.atomic context? Yes it would,
                # except that some webhook handlers can have side effects outside of our local database, meaning that
                # even if we rollback on our database, some updates may have been sent to Stripe, etc in resposne to
                # webhooks...
                webhooks.call_handlers(self, self.message, self.event_type, self.event_subtype)
                self._send_signal()
                self.processed = True
            except StripeError as exc:
                # TODO: What if we caught all exceptions or a broader range of exceptions here? How about DoesNotExist
                # exceptions, for instance? or how about TypeErrors, KeyErrors, ValueErrors, etc?
                exc_value = exc
                self.processed = False
                EventProcessingException.log(
                    data=exc.http_body,
                    exception=exc,
                    event=self
                )
                webhook_processing_error.send(
                    sender=Event,
                    data=exc.http_body,
                    exception=exc
                )

            # Saving here now because a previously processed webhook may no
            # longer be processsed successfully if a re-process was forced but
            # an event handle was broken.
            self.save()

            if exc_value and raise_exception:
                six.reraise(StripeError, exc_value)

        return self.processed

    def _send_signal(self):
        signal = WEBHOOK_SIGNALS.get(self.type)
        if signal:
            return signal.send(sender=Event, event=self)

    @cached_property
    def parts(self):
        """ Gets the event type/subtype as a list of parts. """
        return str(self.type).split(".")

    @cached_property
    def event_type(self):
        """ Gets the event type string. """
        return self.parts[0]

    @cached_property
    def event_subtype(self):
        """ Gets the event subtype string. """
        return ".".join(self.parts[1:])


@class_doc_inherit
class Transfer(StripeTransfer):
    __doc__ = getattr(StripeTransfer, "__doc__")

    # account = ForeignKey("Account", related_name="transfers")

    objects = TransferManager()


# ============================================================================ #
#                                   Connect                                    #
# ============================================================================ #

class Account(StripeAccount):
    pass


# ============================================================================ #
#                               Payment Methods                                #
# ============================================================================ #

@class_doc_inherit
class Card(StripeCard):
    __doc__ = getattr(StripeCard, "__doc__")

    # account = ForeignKey("Account", null=True, related_name="cards")

    def _attach_objects_hook(self, cls, data):
        customer = cls._stripe_object_to_customer(target_cls=Customer, data=data)
        if customer:
            self.customer = customer
        else:
            raise ValidationError("A customer was not attached to this card.")

    def remove(self):
        """Removes a card from this customer's account."""

        try:
            self._api_delete()
        except InvalidRequestError as exc:
            if str(exc).startswith("No such customer:"):
                # The exception was thrown because the stripe customer was already
                # deleted on the stripe side, ignore the exception
                pass
            else:
                # The exception was raised for another reason, re-raise it
                six.reraise(*sys.exc_info())

        self.delete()


# ============================================================================ #
#                                Subscriptions                                 #
# ============================================================================ #


@class_doc_inherit
class Invoice(StripeInvoice):
    __doc__ = getattr(StripeInvoice, "__doc__")

    # account = ForeignKey("Account", related_name="invoices")
    customer = ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name="invoices",
        help_text="The customer associated with this invoice."
    )
    charge = OneToOneField(
        Charge,
        null=True, on_delete=models.CASCADE,
        related_name="invoice",
        help_text="The latest charge generated for this invoice, if any."
    )
    subscription = ForeignKey(
        "Subscription",
        null=True,
        related_name="invoices",
        on_delete=SET_NULL,
        help_text="The subscription that this invoice was prepared for, if any."
    )

    class Meta(object):
        ordering = ["-date"]

    def _attach_objects_hook(self, cls, data):
        self.customer = cls._stripe_object_to_customer(target_cls=Customer, data=data)

        charge = cls._stripe_object_to_charge(target_cls=Charge, data=data)
        if charge:
            if djstripe_settings.SEND_INVOICE_RECEIPT_EMAILS:
                charge.send_receipt()

            self.charge = charge

        subscription = cls._stripe_object_to_subscription(target_cls=Subscription, data=data)
        if subscription:
            self.subscription = subscription

    def _attach_objects_post_save_hook(self, cls, data):
        # InvoiceItems need a saved invoice because they're associated via a
        # RelatedManager, so this must be done as part of the post save hook.
        cls._stripe_object_to_invoice_items(target_cls=InvoiceItem, data=data, invoice=self)

    @classmethod
    def upcoming(cls, **kwargs):
        # Convert Customer to stripe_id
        if "customer" in kwargs and isinstance(kwargs["customer"], Customer):
            kwargs.update({"customer": kwargs["customer"].stripe_id})

        # Convert Subscription to stripe_id
        if "subscription" in kwargs and isinstance(kwargs["subscription"], Subscription):
            kwargs.update({"subscription": kwargs["subscription"].stripe_id})

        # Convert Plan to stripe_id
        if "subscription_plan" in kwargs and isinstance(kwargs["subscription_plan"], Plan):
            kwargs.update({"subscription_plan": kwargs["subscription_plan"].stripe_id})

        upcoming_stripe_invoice = StripeInvoice.upcoming(**kwargs)

        if upcoming_stripe_invoice:
            return UpcomingInvoice._create_from_stripe_object(upcoming_stripe_invoice, save=False)

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


@class_doc_inherit
class UpcomingInvoice(Invoice):
    __doc__ = getattr(Invoice, "__doc__")

    def __init__(self, *args, **kwargs):
        super(UpcomingInvoice, self).__init__(*args, **kwargs)
        self._invoiceitems = []

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

        return QuerySetMock(InvoiceItem, *self._invoiceitems)

    @property
    def stripe_id(self):
        return None

    @stripe_id.setter
    def stripe_id(self, value):
        return  # noop

    def save(self, *args, **kwargs):
        return  # noop


@class_doc_inherit
class InvoiceItem(StripeInvoiceItem):
    __doc__ = getattr(StripeInvoiceItem, "__doc__")

    # account = ForeignKey(Account, related_name="invoiceitems")
    customer = ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name="invoiceitems",
        help_text="The customer associated with this invoiceitem."
    )
    invoice = ForeignKey(
        Invoice, on_delete=models.CASCADE,
        null=True,
        related_name="invoiceitems",
        help_text="The invoice to which this invoiceitem is attached."
    )
    plan = ForeignKey(
        "Plan",
        null=True,
        related_name="invoiceitems",
        on_delete=SET_NULL,
        help_text="If the invoice item is a proration, the plan of the subscription for which the proration was "
        "computed."
    )
    subscription = ForeignKey(
        "Subscription",
        null=True,
        related_name="invoiceitems",
        on_delete=SET_NULL,
        help_text="The subscription that this invoice item has been created for, if any."
    )

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


@class_doc_inherit
class Plan(StripePlan):
    __doc__ = getattr(StripePlan, "__doc__")

    # account = ForeignKey("Account", related_name="plans")

    class Meta(object):
        ordering = ["amount"]

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


@class_doc_inherit
class Subscription(StripeSubscription):
    __doc__ = getattr(StripeSubscription, "__doc__")

    # account = ForeignKey("Account", related_name="subscriptions")
    customer = ForeignKey(
        "Customer", on_delete=models.CASCADE,
        related_name="subscriptions",
        help_text="The customer associated with this subscription."
    )
    plan = ForeignKey(
        "Plan", on_delete=models.CASCADE,
        related_name="subscriptions",
        help_text="The plan associated with this subscription."
    )

    objects = SubscriptionManager()

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

    def update(self, prorate=djstripe_settings.PRORATION_POLICY, **kwargs):
        # Convert Plan to stripe_id
        if "plan" in kwargs and isinstance(kwargs["plan"], Plan):
            kwargs.update({"plan": kwargs["plan"].stripe_id})

        stripe_subscription = super(Subscription, self).update(prorate=prorate, **kwargs)
        return Subscription.sync_from_stripe_data(stripe_subscription)

    def extend(self, delta):
        stripe_subscription = super(Subscription, self).extend(delta)
        return Subscription.sync_from_stripe_data(stripe_subscription)

    def cancel(self, at_period_end=djstripe_settings.CANCELLATION_AT_PERIOD_END):
        # If plan has trial days and customer cancels before trial period ends, then end subscription now,
        #     i.e. at_period_end=False
        if self.trial_end and self.trial_end > timezone.now():
            at_period_end = False

        stripe_subscription = super(Subscription, self).cancel(at_period_end=at_period_end)
        return Subscription.sync_from_stripe_data(stripe_subscription)

    def _attach_objects_hook(self, cls, data):
        self.customer = cls._stripe_object_to_customer(target_cls=Customer, data=data)
        self.plan = cls._stripe_object_to_plan(target_cls=Plan, data=data)


# ============================================================================ #
#                             DJ-STRIPE RESOURCES                              #
# ============================================================================ #

@python_2_unicode_compatible
class EventProcessingException(TimeStampedModel):
    event = ForeignKey("Event", on_delete=models.CASCADE, null=True)
    data = TextField()
    message = CharField(max_length=500)
    traceback = TextField()

    @classmethod
    def log(cls, data, exception, event):
        cls.objects.create(
            event=event,
            data=data or "",
            message=str(exception),
            traceback=exception_traceback.format_exc()
        )

    def __str__(self):
        return smart_text("<{message}, pk={pk}, Event={event}>".format(
            message=self.message,
            pk=self.pk,
            event=self.event
        ))


# Much like registering signal handlers. We import this module so that its registrations get picked up
# the NO QA directive tells flake8 to not complain about the unused import
from . import event_handlers  # NOQA
