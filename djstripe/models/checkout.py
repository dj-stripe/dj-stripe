import stripe
from django.db import models

from .. import enums
from ..fields import JSONField, StripeEnumField
from .base import StripeModel


class Session(StripeModel):
    """
    A Checkout Session represents your customer's session as they pay
    for one-time purchases or subscriptions through Checkout.
    """

    stripe_class = stripe.checkout.Session

    billing_address_collection = StripeEnumField(
        enum=enums.SessionBillingAddressCollection,
        blank=True,
        help_text=(
            "The value (auto or required) for whether Checkout"
            "collected the customer’s billing address."
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
    customer = models.ForeignKey(
        "Customer",
        null=True,
        on_delete=models.SET_NULL,
        help_text=("Customer this Checkout is for if one exists."),
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
        help_text=("The line items, plans, or SKUs purchased by the customer."),
    )
    locale = models.CharField(
        max_length=255,
        blank=True,
        help_text=(
            "The IETF language tag of the locale Checkout is displayed in."
            "If blank or auto, the browser’s locale is used."
        ),
    )
    mode = StripeEnumField(
        enum=enums.SessionMode,
        blank=True,
        help_text="The mode of the Checkout Session, "
        "one of payment, setup, or subscription.",
    )
    payment_intent = models.ForeignKey(
        "PaymentIntent",
        null=True,
        on_delete=models.SET_NULL,
        help_text=("PaymentIntent created if SKUs or line items were provided."),
    )
    payment_method_types = JSONField(
        help_text="The list of payment method types (e.g. card) that this "
        "Checkout Session is allowed to accept."
    )
    submit_type = StripeEnumField(
        enum=enums.SubmitTypeStatus,
        blank=True,
        help_text="Describes the type of transaction being performed by Checkout"
        "in order to customize relevant text on the page, such as the submit button.",
    )
    subscription = models.ForeignKey(
        "Subscription",
        null=True,
        on_delete=models.SET_NULL,
        help_text=("Subscription created if one or more plans were provided."),
    )
    success_url = models.TextField(
        max_length=5000,
        blank=True,
        help_text=(
            "The URL the customer will be directed to after the payment or subscription"
            "creation is successful."
        ),
    )
