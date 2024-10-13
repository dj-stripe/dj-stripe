import stripe
from django.db import models

from djstripe.settings import djstripe_settings

from ..fields import StripeForeignKey
from ..models import Subscription
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
        "customer",
        "payment_intent",
        "subscription",
    ]
    stripe_class = stripe.checkout.Session

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
    customer = StripeForeignKey(
        "Customer",
        null=True,
        on_delete=models.SET_NULL,
        help_text="Customer this Checkout is for if one exists.",
    )

    @property
    def amount_subtotal(self) -> int | None:
        return self.stripe_data.get("amount_subtotal")

    @property
    def amount_total(self) -> int | None:
        return self.stripe_data.get("amount_total")

    @property
    def currency(self) -> str:
        return self.stripe_data.get("currency", "")

    @property
    def customer_email(self) -> str:
        return self.stripe_data.get("customer_email", "")

    @property
    def locale(self) -> str:
        return self.stripe_data.get("locale", "")

    @property
    def mode(self) -> str:
        return self.stripe_data.get("mode", "")

    @property
    def status(self) -> str:
        return self.stripe_data.get("status", "")

    @property
    def subscription(self) -> Subscription | None:
        subscription = self.stripe_data.get("subscription")
        if subscription and isinstance(subscription, str):
            return Subscription.objects.filter(id=subscription).first()

        return None

    @property
    def url(self) -> str:
        return self.stripe_data.get("url") or ""

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
