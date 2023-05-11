"""Stripe Fraud module."""
import stripe
from django.db import models
from django.utils.translation import gettext_lazy as _

from djstripe.settings import djstripe_settings

from ..enums import ReviewClosedReasons, ReviewOpenedReasons, ReviewReasons
from ..fields import JSONField, StripeEnumField, StripeForeignKey
from ..models import StripeModel


class Review(StripeModel):
    """
    Reviews can be used to supplement automated fraud
    detection with human expertise..

    Stripe API reference: https://stripe.com/docs/api/radar/reviews?lang=python
    """

    expand_fields = ["charge", "payment_intent"]
    stripe_class = stripe.Review
    # todo just a guess. Need to somehow find and update it.
    stripe_dashboard_item_name = "reviews"

    metadata = None
    description = None
    open = models.BooleanField(
        help_text=_("If true, the review needs action."),
    )
    charge = StripeForeignKey(
        "Charge",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviews",
        help_text="The charge associated with this review.",
    )
    reason = StripeEnumField(enum=ReviewReasons)
    payment_intent = StripeForeignKey(
        "PaymentIntent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviews",
        help_text="The PaymentIntent ID associated with this review, if one exists.",
    )
    billing_zip = models.CharField(
        max_length=255,
        help_text=_("The ZIP or postal code of the card used, if applicable."),
    )
    closed_reason = StripeEnumField(enum=ReviewClosedReasons)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("The IP address where the payment originated."),
    )
    ip_address_location = JSONField(
        null=True,
        blank=True,
        help_text=_(
            "nformation related to the location of the payment. Note that this information is an approximation and attempts to locate the nearest population center - it should not be used to determine a specific address."
        ),
    )
    opened_reason = StripeEnumField(enum=ReviewOpenedReasons)
    session = JSONField(
        null=True,
        blank=True,
        help_text=_(
            "Information related to the browsing session of the user who initiated the payment."
        ),
    )

    def __str__(self):
        return f"({self.open}) for {self.charge})"

    def approve(self, api_key=None, stripe_account=None):
        """
        Call the stripe API's approve operation for this model.

        :param api_key: The api key to use for this request. \
            Defaults to djstripe_settings.STRIPE_SECRET_KEY.
        :type api_key: string
        :param stripe_account: The optional connected account \
            for which this request is being made.
        :type stripe_account: string
        """
        # Prefer passed in stripe_account if set.
        if not stripe_account:
            stripe_account = self._get_stripe_account_id(api_key)

        return self.stripe_class.approve(
            self.id,
            api_key=api_key or self.default_api_key,
            stripe_version=djstripe_settings.STRIPE_API_VERSION,
            stripe_account=stripe_account,
        )
