import stripe
from django.db import models

from djstripe.settings import djstripe_settings

from .. import enums
from ..fields import (
    JSONField,
    StripeCurrencyCodeField,
    StripeEnumField,
    StripeForeignKey,
    StripeQuantumCurrencyAmountField,
)
from .base import StripeModel


class Session(StripeModel):
    """
    A Checkout Session represents your customer's session as they pay
    for one-time purchases or subscriptions through Checkout.

    Stripe documentation: https://stripe.com/docs/api/checkout/sessions?lang=python
    """

    expand_fields = [
        "line_items",
        "total_details.breakdown",
        "line_items.data.discounts",
    ]
    stripe_class = stripe.checkout.Session

    amount_total = StripeQuantumCurrencyAmountField(
        null=True,
        blank=True,
        help_text="Total of all items after discounts and taxes are applied.",
    )
    amount_subtotal = StripeQuantumCurrencyAmountField(
        null=True,
        blank=True,
        help_text="Total of all items after discounts and taxes are applied.",
    )
    billing_address_collection = StripeEnumField(
        enum=enums.SessionBillingAddressCollection,
        blank=True,
        help_text=(
            "The value (auto or required) for whether Checkout"
            "collected the customer's billing address."
        ),
    )
    cancel_url = models.TextField(
        max_length=5000,
        blank=True,
        help_text=(
            "The URL the customer will be directed to if they"
            "decide to cancel payment and return to your website."
        ),
    )
    client_reference_id = models.TextField(
        max_length=5000,
        blank=True,
        help_text=(
            "A unique string to reference the Checkout Session."
            "This can be a customer ID, a cart ID, or similar, and"
            "can be used to reconcile the session with your internal systems."
        ),
    )
    currency = StripeCurrencyCodeField(
        null=True,
        blank=True,
        help_text=(
            "Three-letter ISO currency code, in lowercase. Must be a supported"
            " currency."
        ),
    )
    customer = StripeForeignKey(
        "Customer",
        null=True,
        on_delete=models.SET_NULL,
        help_text="Customer this Checkout is for if one exists.",
    )
    customer_email = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "If provided, this value will be used when the Customer object is created."
        ),
    )
    display_items = JSONField(
        null=True,
        blank=True,
        help_text="The line items, plans, or SKUs purchased by the customer.",
    )
    line_items = JSONField(
        null=True,
        blank=True,
        help_text="The line items purchased by the customer.",
    )
    locale = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "The IETF language tag of the locale Checkout is displayed in."
            "If blank or auto, the browser's locale is used."
        ),
    )
    mode = StripeEnumField(
        enum=enums.SessionMode,
        blank=True,
        help_text=(
            "The mode of the Checkout Session, one of payment, setup, or subscription."
        ),
    )
    payment_intent = StripeForeignKey(
        "PaymentIntent",
        null=True,
        on_delete=models.SET_NULL,
        help_text="PaymentIntent created if SKUs or line items were provided.",
    )
    payment_method_types = JSONField(
        help_text=(
            "The list of payment method types (e.g. card) that this "
            "Checkout Session is allowed to accept."
        )
    )
    payment_status = StripeEnumField(
        enum=enums.SessionPaymentStatus,
        null=True,
        blank=True,
        help_text=(
            "The payment status of the Checkout Session, one of paid, unpaid, or"
            " no_payment_required. You can use this value to decide when to fulfill"
            " your customer's order."
        ),
    )
    setup_intent = StripeForeignKey(
        "SetupIntent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="The ID of the SetupIntent for Checkout Sessions in setup mode.",
    )
    shipping_address_collection = JSONField(
        null=True,
        blank=True,
        help_text=(
            "When set, provides configuration for Checkout to collect a shipping"
            " address from a customer."
        ),
    )
    shipping_cost = JSONField(
        null=True,
        blank=True,
        help_text=(
            "The details of the customer cost of shipping, including the customer"
            " chosen ShippingRate."
        ),
    )
    shipping_details = JSONField(
        null=True,
        blank=True,
        help_text="Shipping information for this Checkout Session.",
    )
    shipping_options = JSONField(
        null=True,
        blank=True,
        help_text="The shipping rate options applied to this Session.",
    )
    status = StripeEnumField(
        enum=enums.SessionStatus,
        null=True,
        blank=True,
        help_text=(
            "The status of the Checkout Session, one of open, complete, or expired."
        ),
    )
    submit_type = StripeEnumField(
        enum=enums.SubmitTypeStatus,
        blank=True,
        help_text=(
            "Describes the type of transaction being performed by Checkoutin order to"
            " customize relevant text on the page, such as the submit button."
        ),
    )
    subscription = StripeForeignKey(
        "Subscription",
        null=True,
        on_delete=models.SET_NULL,
        help_text="Subscription created if one or more plans were provided.",
    )
    success_url = models.TextField(
        max_length=5000,
        blank=True,
        help_text=(
            "The URL the customer will be directed to after the payment or subscription"
            "creation is successful."
        ),
    )
    total_details = JSONField(
        null=True,
        blank=True,
        help_text="Tax and discount details for the computed total amount.",
    )
    url = models.TextField(
        max_length=5000,
        blank=True,
        null=True,
        help_text=(
            "The URL to the Checkout Session. Redirect customers to this URL to take"
            " them to Checkout. If you’re using Custom Domains, the URL will use your"
            " subdomain. Otherwise, it’ll use checkout.stripe.com. This value is only"
            " present when the session is active."
        ),
    )

    def _attach_objects_post_save_hook(
        self,
        cls,
        data,
        api_key=djstripe_settings.STRIPE_SECRET_KEY,
        pending_relations=None,
    ):
        from ..event_handlers import update_customer_helper

        super()._attach_objects_post_save_hook(
            cls, data, api_key=api_key, pending_relations=pending_relations
        )

        # only update if customer and metadata exist
        if self.customer and self.metadata:
            key = djstripe_settings.SUBSCRIBER_CUSTOMER_KEY
            current_value = self.metadata.get(key)

            # only update if metadata has the SUBSCRIBER_CUSTOMER_KEY
            if current_value:
                metadata = {key: current_value}

                # Update the customer with ONLY the customer specific metadata
                update_customer_helper(
                    metadata,
                    self.customer.id,
                    key,
                )

                # Update metadata in the Upstream Customer Object on Stripe
                self.customer._api_update(metadata=metadata)
