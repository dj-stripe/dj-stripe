import stripe
from django.db import models

from djstripe.settings import djstripe_settings

from .. import enums
from ..fields import (
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
    client_reference_id = models.TextField(
        max_length=5000,
        blank=True,
        help_text=(
            "A unique string to reference the Checkout Session."
            "This can be a customer ID, a cart ID, or similar, and"
            "can be used to reconcile the session with your internal systems."
        ),
        db_index=True,
    )
    currency = StripeCurrencyCodeField(null=True, blank=True)
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
        db_index=True,
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
    status = StripeEnumField(
        enum=enums.SessionStatus,
        null=True,
        blank=True,
        help_text=(
            "The status of the Checkout Session, one of open, complete, or expired."
        ),
    )

    @property
    def url(self) -> str:
        return self.stripe_data.get("url") or ""

    @property
    def subscription(self) -> "Subscription" | None:
        from ..models import Subscription

        subscription = self.stripe_data.get("subscription")
        if subscription and isinstance(subscription, str):
            return Subscription.objects.filter(id=subscription).first()

        return None

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
