"""Stripe Fraud module."""
import stripe
from django.db import models
from django.utils.translation import gettext_lazy as _

from ..enums import EarlyFraudWarningFraudTypes
from ..fields import StripeEnumField, StripeForeignKey
from ..models import StripeModel


class EarlyFraudWarning(StripeModel):
    """
    An early fraud warning indicates that the card issuer has
    notified us that a charge may be fraudulent.

    Stripe API reference: https://stripe.com/docs/api/radar/early_fraud_warnings?lang=python
    """

    expand_fields = ["charge", "payment_intent"]
    stripe_class = stripe.radar.EarlyFraudWarning
    # todo just a guess. Need to somehow find and update it.
    stripe_dashboard_item_name = "early_fraud_warning"

    metadata = None
    description = None
    actionable = models.BooleanField(
        help_text=_(
            "An EFW is actionable if it has not received a dispute and has not been fully refunded. You may wish to proactively refund a charge that receives an EFW, in order to avoid receiving a dispute later."
        ),
    )
    charge = StripeForeignKey(
        "Charge",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="early_fraud_warnings",
        help_text="ID of the charge this early fraud warning is for, optionally expanded.",
    )
    fraud_type = StripeEnumField(enum=EarlyFraudWarningFraudTypes)
    payment_intent = StripeForeignKey(
        "PaymentIntent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="early_fraud_warnings",
        help_text="ID of the Payment Intent this early fraud warning is for, optionally expanded.",
    )

    def __str__(self):
        return f"{self.fraud_type} for {self.charge})"
