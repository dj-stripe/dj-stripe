import decimal

import stripe
from django.db import models
from django.db.models.deletion import SET_NULL
from django.utils import timezone
from django.utils.functional import cached_property
from stripe.error import InvalidRequestError

from .. import enums
from .. import settings as djstripe_settings
from .. import webhooks
from ..exceptions import MultipleSubscriptionException
from ..fields import (
    PaymentMethodForeignKey, StripeBooleanField, StripeCharField,
    StripeCurrencyField, StripeDateTimeField, StripeEnumField, StripeIdField,
    StripeIntegerField, StripeJSONField, StripeNullBooleanField, StripeTextField
)
from ..managers import ChargeManager
from ..signals import WEBHOOK_SIGNALS
from ..utils import get_friendly_currency_amount
from .base import StripeObject, logger
from .connect import Account, Transfer


# Override the default API version used by the Stripe library.
djstripe_settings.set_stripe_api_version()


# TODO: class Balance(...)


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
        "uncaptured or has since been captured.",
    )
    currency = StripeCharField(
        max_length=3,
        help_text="Three-letter ISO currency code representing the currency in which the charge was made.",
    )
    customer = models.ForeignKey(
        "Customer",
        on_delete=models.CASCADE,
        null=True,
        related_name="charges",
        help_text="The customer associated with this charge.",
    )
    # XXX: destination
    account = models.ForeignKey(
        "Account",
        on_delete=models.CASCADE,
        null=True,
        related_name="charges",
        help_text="The account the charge was made on behalf of. Null here indicates that this value was never set.",
    )
    dispute = models.ForeignKey(
        "Dispute",
        on_delete=models.SET_NULL,
        null=True,
        related_name="charges",
        help_text="Details about the dispute if the charge has been disputed.",
    )
    failure_code = StripeEnumField(
        enum=enums.ApiErrorCode,
        null=True,
        help_text="Error code explaining reason for charge failure if available.",
    )
    failure_message = StripeTextField(
        null=True,
        help_text="Message to user further explaining reason for charge failure if available.",
    )
    fraud_details = StripeJSONField(
        help_text="Hash with information on fraud assessments for the charge."
    )
    invoice = models.ForeignKey(
        "Invoice",
        on_delete=models.CASCADE,
        null=True,
        related_name="charges",
        help_text="The invoice this charge is for if one exists.",
    )
    # TODO: on_behalf_of, order
    outcome = StripeJSONField(
        help_text="Details about whether or not the payment was accepted, and why."
    )
    paid = StripeBooleanField(
        default=False,
        help_text="True if the charge succeeded, or was successfully authorized for later capture, False otherwise.",
    )
    receipt_email = StripeCharField(
        null=True,
        max_length=800,  # yup, 800.
        help_text="The email address that the receipt for this charge was sent to.",
    )
    receipt_number = StripeCharField(
        null=True,
        max_length=14,
        help_text="The transaction number that appears on email receipts sent for this charge.",
    )
    refunded = StripeBooleanField(
        default=False,
        help_text="Whether or not the charge has been fully refunded. If the charge is only partially refunded, "
        "this attribute will still be false.",
    )
    # TODO: review
    shipping = StripeJSONField(
        null=True, help_text="Shipping information for the charge"
    )
    source = PaymentMethodForeignKey(
        on_delete=SET_NULL,
        null=True,
        related_name="charges",
        help_text="The source used for this charge.",
    )
    # TODO: source_transfer
    statement_descriptor = StripeCharField(
        max_length=22,
        null=True,
        help_text="An arbitrary string to be displayed on your customer's credit card statement. The statement "
        "description may not include <>\"' characters, and will appear on your customer's statement in capital "
        "letters. Non-ASCII characters are automatically stripped. While most banks display this information "
        "consistently, some may display it incorrectly or not at all.",
    )
    status = StripeEnumField(
        enum=enums.ChargeStatus, help_text="The status of the payment."
    )
    transfer = models.ForeignKey(
        "Transfer",
        null=True,
        on_delete=models.CASCADE,
        help_text="The transfer to the destination account (only applicable if the charge was created using the "
        "destination parameter).",
    )
    transfer_group = StripeCharField(
        max_length=255,
        stripe_required=False,
        help_text="A string that identifies this transaction as part of a group.",
    )

    # Everything below remains to be cleaned up
    # Balance transaction can be null if the charge failed
    fee = StripeCurrencyField(stripe_required=False, nested_name="balance_transaction")
    fee_details = StripeJSONField(
        stripe_required=False, nested_name="balance_transaction"
    )

    # dj-stripe custom stripe fields. Don't try to send these.
    source_type = StripeEnumField(
        null=True,
        enum=enums.LegacySourceType,
        stripe_name="source.object",
        help_text="The payment source type. If the payment source is supported by dj-stripe, a corresponding model is "
        "attached to this Charge via a foreign key matching this field.",
    )
    source_stripe_id = StripeIdField(
        null=True, stripe_name="source.id", help_text="The payment source id."
    )
    fraudulent = StripeBooleanField(
        default=False, help_text="Whether or not this charge was marked as fraudulent."
    )

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
        from .payment_methods import PaymentMethod

        customer = cls._stripe_object_to_customer(target_cls=Customer, data=data)
        if customer:
            self.customer = customer

        transfer = cls._stripe_object_to_transfer(target_cls=Transfer, data=data)
        if transfer:
            self.transfer = transfer

        # Set the account on this object.
        destination_account = cls._stripe_object_destination_to_account(
            target_cls=Account, data=data
        )
        if destination_account:
            self.account = destination_account
        else:
            self.account = Account.get_default_account()

        self.source, _ = PaymentMethod._get_or_create_source(
            data["source"], self.source_type
        )

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
            amount=self._calculate_refund_amount(amount=amount), reason=reason
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
        data["fraudulent"] = (
            bool(data["fraud_details"])
            and list(data["fraud_details"].values())[0] == "fraudulent"
        )

        return data


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
        max_length=20,
        stripe_required=False,
        help_text="The customer's VAT identification number.",
    )
    currency = StripeCharField(
        max_length=3,
        null=True,
        help_text="The currency the customer can be charged in for recurring billing purposes (subscriptions, "
        "invoices, invoice items).",
    )
    default_source = PaymentMethodForeignKey(
        on_delete=SET_NULL, null=True, related_name="customers"
    )
    delinquent = StripeBooleanField(
        help_text="Whether or not the latest charge for the customer's latest invoice has failed."
    )
    # <discount>
    coupon = models.ForeignKey("Coupon", null=True, blank=True, on_delete=SET_NULL)
    coupon_start = StripeDateTimeField(
        null=True,
        editable=False,
        stripe_name="discount.start",
        stripe_required=False,
        help_text="If a coupon is present, the date at which it was applied.",
    )
    coupon_end = StripeDateTimeField(
        null=True,
        editable=False,
        stripe_name="discount.end",
        stripe_required=False,
        help_text="If a coupon is present and has a limited duration, the date that the discount will end.",
    )
    # </discount>
    email = StripeTextField(null=True)
    shipping = StripeJSONField(
        stripe_required=False,
        help_text="Shipping information associated with the customer.",
    )

    # dj-stripe fields
    subscriber = models.ForeignKey(
        djstripe_settings.get_subscriber_model_string(),
        null=True,
        on_delete=SET_NULL,
        related_name="djstripe_customers",
    )
    date_purged = models.DateTimeField(null=True, editable=False)

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
            idempotency_key = djstripe_settings.get_idempotency_key(
                "customer", action, livemode
            )
            return cls.create(subscriber, idempotency_key=idempotency_key), True

    @classmethod
    def create(cls, subscriber, idempotency_key=None):
        stripe_customer = cls._api_create(
            email=subscriber.email,
            idempotency_key=idempotency_key,
            metadata={cls.djstripe_subscriber_key: subscriber.pk},
        )
        customer, created = Customer.objects.get_or_create(
            stripe_id=stripe_customer["id"],
            defaults={
                "subscriber": subscriber,
                "livemode": stripe_customer["livemode"],
                "account_balance": stripe_customer.get("account_balance", 0),
                "delinquent": stripe_customer.get("delinquent", False),
            },
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
        self,
        plan,
        charge_immediately=True,
        application_fee_percent=None,
        coupon=None,
        quantity=None,
        metadata=None,
        tax_percent=None,
        trial_end=None,
        trial_from_plan=None,
        trial_period_days=None,
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
        from .billing import Plan, Subscription

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
        self,
        amount,
        currency=None,
        application_fee=None,
        capture=None,
        description=None,
        destination=None,
        metadata=None,
        shipping=None,
        source=None,
        statement_descriptor=None,
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
        if source and isinstance(source, StripeObject):
            source = source.stripe_id

        stripe_charge = Charge._api_create(
            amount=int(amount * 100),  # Convert dollars into cents
            currency=currency,
            application_fee=int(application_fee * 100)
            if application_fee
            else None,  # Convert dollars into cents
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
        self,
        amount,
        currency,
        description=None,
        discountable=None,
        invoice=None,
        metadata=None,
        subscription=None,
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
        from .billing import InvoiceItem

        if not isinstance(amount, decimal.Decimal):
            raise ValueError("You must supply a decimal value representing dollars.")

        # Convert Invoice to stripe_id
        if invoice is not None and isinstance(invoice, StripeObject):
            invoice = invoice.stripe_id

        # Convert Subscription to stripe_id
        if subscription is not None and isinstance(subscription, StripeObject):
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
        from .payment_methods import PaymentMethod

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
            if "No such customer:" in str(exc):
                # The exception was thrown because the stripe customer was already
                # deleted on the stripe side, ignore the exception
                pass
            else:
                # The exception was raised for another reason, re-raise it
                raise

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

        return [
            subscription
            for subscription in self.subscriptions.all()
            if subscription.is_valid()
        ]

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
                raise TypeError(
                    "plan cannot be None if more than one valid subscription exists for this customer."
                )

        else:
            # Convert Plan to stripe_id
            if isinstance(plan, StripeObject):
                plan = plan.stripe_id

            return any(
                [
                    subscription.is_valid()
                    for subscription in self.subscriptions.filter(plan__stripe_id=plan)
                ]
            )

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
            status=enums.SubscriptionStatus.active,
            current_period_end__gt=timezone.now(),
        )

    @property
    def valid_subscriptions(self):
        """Returns this cusotmer's valid subscriptions (subscriptions that aren't cancelled."""
        return self.subscriptions.exclude(status=enums.SubscriptionStatus.canceled)

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
            raise MultipleSubscriptionException(
                "This customer has multiple subscriptions. Use Customer.subscriptions "
                "to access them."
            )
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
        from .billing import Invoice

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
                    raise

    def has_valid_source(self):
        """ Check whether the customer has a valid payment source."""
        return self.default_source is not None

    def add_coupon(self, coupon, idempotency_key=None):
        """
        Add a coupon to a Customer.

        The coupon can be a Coupon object, or a valid Stripe Coupon ID.
        """
        if isinstance(coupon, StripeObject):
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
        from .billing import Invoice

        kwargs["customer"] = self
        return Invoice.upcoming(**kwargs)

    def _attach_objects_post_save_hook(self, cls, data):  # noqa (function complexity)
        from .billing import Coupon
        from .payment_methods import PaymentMethod

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
            if isinstance(default_source, str):
                default_source_id = default_source
            else:
                default_source_id = default_source["id"]
            source = sources[default_source_id]

            save = self.default_source != source
            self.default_source = source

        discount = data.get("discount")
        if discount:
            coupon, _created = Coupon._get_or_create_from_stripe_object(
                discount, "coupon"
            )
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
                logger.warning(
                    "Could not find subscriber %r matching customer %r",
                    subscriber_id,
                    self.stripe_id,
                )
                self.subscriber = None

    # SYNC methods should be dropped in favor of the master sync infrastructure proposed
    def _sync_invoices(self, **kwargs):
        from .billing import Invoice

        for stripe_invoice in Invoice.api_list(customer=self.stripe_id, **kwargs):
            Invoice.sync_from_stripe_data(stripe_invoice)

    def _sync_charges(self, **kwargs):
        for stripe_charge in Charge.api_list(customer=self.stripe_id, **kwargs):
            Charge.sync_from_stripe_data(stripe_charge)

    def _sync_cards(self, **kwargs):
        from .payment_methods import Card

        for stripe_card in Card.api_list(customer=self, **kwargs):
            Card.sync_from_stripe_data(stripe_card)

    def _sync_subscriptions(self, **kwargs):
        from .billing import Subscription

        for stripe_subscription in Subscription.api_list(
            customer=self.stripe_id, status="all", **kwargs
        ):
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
    currency = StripeCharField(
        max_length=3, help_text="Three-letter ISO currency code."
    )
    evidence = StripeJSONField(help_text="Evidence provided to respond to a dispute.")
    evidence_details = StripeJSONField(
        help_text="Information about the evidence submission."
    )
    is_charge_refundable = StripeBooleanField(
        help_text=(
            "If true, it is still possible to refund the disputed payment. "
            "Once the payment has been fully refunded, no further funds will "
            "be withdrawn from your Stripe account as a result of this dispute."
        )
    )
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
        max_length=15,
        blank=True,
        help_text="the API version at which the event data was "
        "rendered. Blank for old entries only, all new entries will have this value",
    )
    data = StripeJSONField(
        help_text="data received at webhook. data should be considered to be garbage until validity check is run "
        "and valid flag is set"
    )
    request_id = StripeCharField(
        max_length=50,
        help_text="Information about the request that triggered this event, for traceability purposes. If empty "
        "string then this is an old entry without that data. If Null then this is not an old entry, but a Stripe "
        "'automated' event with no associated request.",
        stripe_required=False,
    )
    idempotency_key = StripeTextField(null=True, blank=True, stripe_required=False)
    type = StripeCharField(max_length=250, help_text="Stripe's event description code")

    def str_parts(self):
        return ["type={type}".format(type=self.type)] + super().str_parts()

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
        return str(self.type).split(".")

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
        max_length=255,
        help_text="A filename for the file, suitable for saving to a filesystem.",
    )
    purpose = StripeEnumField(
        enum=enums.FileUploadPurpose, help_text="The purpose of the uploaded file."
    )
    size = StripeIntegerField(help_text="The size in bytes of the file upload object.")
    type = StripeEnumField(
        enum=enums.FileUploadType, help_text="The type of the file returned."
    )
    url = StripeCharField(
        max_length=200,
        help_text="A read-only URL where the uploaded file can be accessed.",
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
    # TODO: balance_transaction = models.ForeignKey("Transaction")  txn_...
    currency = StripeCharField(
        max_length=3, help_text="Three-letter ISO currency code."
    )
    destination = models.ForeignKey(
        "BankAccount",
        on_delete=models.PROTECT,
        null=True,
        help_text="ID of the bank account or card the payout was sent to.",
    )
    # TODO: failure_balance_transaction = ForeignKey("Transaction", null=True)
    failure_code = StripeEnumField(
        enum=enums.PayoutFailureCode,
        blank=True,
        null=True,
        help_text="Error code explaining reason for transfer failure if available. "
        "See https://stripe.com/docs/api/python#transfer_failures.",
    )
    failure_message = StripeTextField(
        null=True,
        blank=True,
        help_text="Message to user further explaining reason for payout failure if available.",
    )
    method = StripeEnumField(
        max_length=8,
        enum=enums.PayoutMethod,
        help_text=(
            "The method used to send this payout. "
            "`instant` is only supported for payouts to debit cards."
        ),
    )
    # TODO: source_type
    statement_descriptor = StripeCharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Extra information about a payout to be displayed on the user's bank statement.",
    )
    status = StripeEnumField(
        enum=enums.PayoutStatus,
        help_text=(
            "Current status of the payout. "
            "A payout will be `pending` until it is submitted to the bank, at which point it "
            "becomes `in_transit`. I t will then change to paid if the transaction goes through. "
            "If it does not go through successfully, its status will change to `failed` or `canceled`."
        ),
    )
    type = StripeEnumField(enum=enums.PayoutType)


class Product(StripeObject):
    """
    https://stripe.com/docs/api#product_object
    """

    stripe_class = stripe.Product
    stripe_dashboard_item_name = "products"

    # Fields applicable to both `good` and `service`
    name = StripeCharField(
        max_length=5000,
        help_text=(
            "The product's name, meant to be displayable to the customer. "
            "Applicable to both `service` and `good` types."
        ),
    )
    type = StripeEnumField(
        enum=enums.ProductType,
        help_text=(
            "The type of the product. The product is either of type `good`, which is "
            "eligible for use with Orders and SKUs, or `service`, which is eligible "
            "for use with Subscriptions and Plans."
        ),
    )

    # Fields applicable to `good` only
    active = StripeNullBooleanField(
        help_text=(
            "Whether the product is currently available for purchase. "
            "Only applicable to products of `type=good`."
        )
    )
    attributes = StripeJSONField(
        null=True,
        help_text=(
            "A list of up to 5 attributes that each SKU can provide values for "
            '(e.g., `["color", "size"]`). Only applicable to products of `type=good`.'
        ),
    )
    caption = StripeCharField(
        null=True,
        max_length=5000,
        help_text=(
            "A short one-line description of the product, meant to be displayable"
            "to the customer. Only applicable to products of `type=good`."
        ),
    )
    deactivate_on = StripeJSONField(
        stripe_required=False,
        help_text=(
            "An array of connect application identifiers that cannot purchase "
            "this product. Only applicable to products of `type=good`."
        ),
    )
    images = StripeJSONField(
        stripe_required=False,
        help_text=(
            "A list of up to 8 URLs of images for this product, meant to be "
            "displayable to the customer. Only applicable to products of `type=good`."
        ),
    )
    package_dimensions = StripeJSONField(
        stripe_required=False,
        help_text=(
            "The dimensions of this product for shipping purposes. "
            "A SKU associated with this product can override this value by having its "
            "own `package_dimensions`. Only applicable to products of `type=good`."
        ),
    )
    shippable = StripeNullBooleanField(
        stripe_required=False,
        help_text=(
            "Whether this product is a shipped good. "
            "Only applicable to products of `type=good`."
        ),
    )
    url = StripeCharField(
        max_length=799,
        null=True,
        help_text=(
            "A URL of a publicly-accessible webpage for this product. "
            "Only applicable to products of `type=good`."
        ),
    )

    # Fields available to `service` only
    statement_descriptor = StripeCharField(
        max_length=22,
        null=True,
        help_text=(
            "Extra information about a product which will appear on your customer's "
            "credit card statement. In the case that multiple products are billed at "
            "once, the first statement descriptor will be used. "
            "Only available on products of type=`service`."
        ),
    )
    unit_label = StripeCharField(max_length=12, null=True)

    def __str__(self):
        return self.name


class Refund(StripeObject):
    """
    https://stripe.com/docs/api#refund_object
    https://stripe.com/docs/refunds
    """

    stripe_class = stripe.Refund

    amount = StripeIntegerField(help_text="Amount, in cents.")
    # balance_transaction = ForeignKey("BalanceTransaction")
    charge = models.ForeignKey(
        "Charge",
        on_delete=models.CASCADE,
        related_name="refunds",
        help_text="The charge that was refunded",
    )
    currency = StripeCharField(max_length=3, help_text="Three-letter ISO currency code")
    # failure_balance_transaction = models.ForeignKey("BalanceTransaction", null=True)
    failure_reason = StripeEnumField(
        enum=enums.RefundFailureReason,
        stripe_required=False,
        help_text="If the refund failed, the reason for refund failure if known.",
    )
    reason = StripeEnumField(
        enum=enums.RefundReason, null=True, help_text="Reason for the refund."
    )
    receipt_number = StripeCharField(
        max_length=9,
        null=True,
        help_text=(
            "The transaction number that appears on email receipts sent for this charge."
        ),
    )
    status = StripeEnumField(
        enum=enums.RefundFailureReason, help_text="Status of the refund."
    )

    def get_stripe_dashboard_url(self):
        return self.charge.get_stripe_dashboard_url()

    def _attach_objects_hook(self, cls, data):
        self.charge = Charge._get_or_create_from_stripe_object(data, "charge")[0]
