import stripe
from django.db import models

from djstripe.settings import djstripe_settings

from ..fields import (
    StripeForeignKey,
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

    # Foreign key fields (kept as Django model fields)
    customer = StripeForeignKey(
        "Customer",
        null=True,
        on_delete=models.SET_NULL,
        help_text="Customer this Checkout is for if one exists.",
    )
    payment_intent = StripeForeignKey(
        "PaymentIntent",
        null=True,
        on_delete=models.SET_NULL,
        help_text="PaymentIntent created if SKUs or line items were provided.",
    )
    setup_intent = StripeForeignKey(
        "SetupIntent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="The ID of the SetupIntent for Checkout Sessions in setup mode.",
    )
    subscription = StripeForeignKey(
        "Subscription",
        null=True,
        on_delete=models.SET_NULL,
        help_text="Subscription created if one or more plans were provided.",
    )

    # Properties for fields stored in stripe_data
    @property
    def amount_total(self):
        """Total of all items after discounts and taxes are applied."""
        return self.stripe_data.get("amount_total")

    @property
    def amount_subtotal(self):
        """Total of all items before discounts and taxes are applied."""
        return self.stripe_data.get("amount_subtotal")

    @property
    def billing_address_collection(self):
        """The value (auto or required) for whether Checkout collected the customer's billing address."""
        return self.stripe_data.get("billing_address_collection")

    @property
    def cancel_url(self):
        """The URL the customer will be directed to if they decide to cancel payment and return to your website."""
        return self.stripe_data.get("cancel_url", "")

    @property
    def client_reference_id(self):
        """A unique string to reference the Checkout Session."""
        return self.stripe_data.get("client_reference_id", "")

    @property
    def currency(self):
        """Three-letter ISO currency code, in lowercase. Must be a supported currency."""
        return self.stripe_data.get("currency")

    @property
    def customer_email(self):
        """If provided, this value will be used when the Customer object is created."""
        return self.stripe_data.get("customer_email", "")

    @property
    def display_items(self):
        """The line items, plans, or SKUs purchased by the customer."""
        return self.stripe_data.get("display_items")

    @property
    def line_items(self):
        """The line items purchased by the customer."""
        return self.stripe_data.get("line_items")

    @property
    def locale(self):
        """The IETF language tag of the locale Checkout is displayed in."""
        return self.stripe_data.get("locale", "")

    @property
    def mode(self):
        """The mode of the Checkout Session, one of payment, setup, or subscription."""
        return self.stripe_data.get("mode")

    @property
    def payment_method_types(self):
        """The list of payment method types (e.g. card) that this Checkout Session is allowed to accept."""
        return self.stripe_data.get("payment_method_types", [])

    @property
    def payment_status(self):
        """The payment status of the Checkout Session, one of paid, unpaid, or no_payment_required."""
        return self.stripe_data.get("payment_status")

    @property
    def shipping_address_collection(self):
        """When set, provides configuration for Checkout to collect a shipping address from a customer."""
        return self.stripe_data.get("shipping_address_collection")

    @property
    def shipping_cost(self):
        """The details of the customer cost of shipping, including the customer chosen ShippingRate."""
        return self.stripe_data.get("shipping_cost")

    @property
    def shipping_details(self):
        """Shipping information for this Checkout Session."""
        return self.stripe_data.get("shipping_details")

    @property
    def shipping_options(self):
        """The shipping rate options applied to this Session."""
        return self.stripe_data.get("shipping_options")

    @property
    def status(self):
        """The status of the Checkout Session, one of open, complete, or expired."""
        return self.stripe_data.get("status")

    @property
    def submit_type(self):
        """Describes the type of transaction being performed by Checkout."""
        return self.stripe_data.get("submit_type")

    @property
    def success_url(self):
        """The URL the customer will be directed to after successful payment or subscription creation."""
        return self.stripe_data.get("success_url", "")

    @property
    def total_details(self):
        """Tax and discount details for the computed total amount."""
        return self.stripe_data.get("total_details")

    @property
    def url(self):
        """The URL to the Checkout Session. Redirect customers to this URL to take them to Checkout."""
        return self.stripe_data.get("url")

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
