import stripe
from django.db import models

from .. import enums
from ..fields import JSONField, StripeEnumField, StripeForeignKey
from .base import StripeModel


class VerificationSession(StripeModel):
    """
    A VerificationSession guides you through the process of collecting and verifying
    the identities of your users. It contains details about the type of verification,
    such as what verification check to perform. Only create one VerificationSession
    for each verification in your system.

    A VerificationSession transitions through multiple statuses throughout its
    lifetime as it progresses through the verification flow. The VerificationSession
    contains the user's verified data after verification checks are complete.

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
    A VerificationReport is the result of an attempt to collect and verify data from a user.
    The collection of verification checks performed is determined from the type and options parameters
    used. You can find the result of each verification check performed in the appropriate sub-resource:
    document, id_number, selfie.

    Each VerificationReport contains a copy of any data collected by the user as well as
    reference IDs which can be used to access collected images through the FileUpload API.
    To configure and create VerificationReports, use the VerificationSession API.

    Stripe documentation: https://stripe.com/docs/api/identity/verification_reports
    """

    stripe_class = stripe.identity.VerificationReport

    document = JSONField(null=True, blank=True)
    id_number = JSONField(null=True, blank=True)
    options = JSONField(null=True, blank=True)
    selfie = JSONField(null=True, blank=True)
    type = StripeEnumField(enum=enums.VerificationType)
