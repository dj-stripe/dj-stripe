import stripe
from django.db import models

from .. import enums
from ..fields import JSONField, StripeEnumField, StripeForeignKey
from .base import StripeModel


class VerificationSession(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/api/identity/verification_sessions
    """

    stripe_class = stripe.identity.VerificationSession

    last_error = JSONField(null=True, blank=True)
    last_verification_report = StripeForeignKey(
        "djstripe.VerificationReport", on_delete=models.SET_NULL, null=True, blank=True
    )
    redaction = JSONField(null=True, blank=True)
    verified_outputs = JSONField(null=True, blank=True)
    status = StripeEnumField(enum=enums.VerificationSessionStatus)
    type = StripeEnumField(enum=enums.VerificationType)

    # The following attributes are not stored because they are sensitive.
    url = None
    client_secret = None


class VerificationReport(StripeModel):
    """
    Stripe documentation: https://stripe.com/docs/api/identity/verification_reports
    """

    stripe_class = stripe.identity.VerificationReport
    expand_fields = ["document.dob", "document.expiration_date", "document.number"]

    document = JSONField(null=True, blank=True)
    id_number = JSONField(null=True, blank=True)
    options = JSONField(null=True, blank=True)
    selfie = JSONField(null=True, blank=True)
    type = StripeEnumField(enum=enums.VerificationType)
