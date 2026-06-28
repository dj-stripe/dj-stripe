"""Custom test assertions used across the dj-stripe test suite."""

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

# Suite-wide allowlist of foreign-key fields that are allowed to be null.
#
# These are fields that Stripe itself treats as nullable AND that tend to be
# null in fixtures (Connect-only metadata, optional branding, optional
# defaults, status-derived links). For any FK in this set, ``assert_fks``
# accepts either None or a populated value — the assertion is "if it's set,
# the link is consistent", not "it must be set".
#
# Tests that need to assert the *opposite* direction ("this specific FK must
# be None in this scenario") still pass it via ``expected_blank_fks=`` and
# ``assert_fks`` will enforce that.
COMMON_BLANK_FKS = frozenset(
    {
        # Account branding
        "djstripe.Account.branding_logo",
        "djstripe.Account.branding_icon",
        # Charge: Connect / dispute / refund related
        "djstripe.Charge.application_fee",
        "djstripe.Charge.dispute",
        "djstripe.Charge.latest_upcominginvoice (related name)",
        "djstripe.Charge.on_behalf_of",
        "djstripe.Charge.refund",
        "djstripe.Charge.source_transfer",
        "djstripe.Charge.transfer",
        # Customer: optional links and back-references
        "djstripe.Customer.coupon",
        "djstripe.Customer.default_payment_method",
        "djstripe.Customer.subscriber",
        # Invoice: default payment options + nested refs
        "djstripe.Invoice.default_payment_method",
        "djstripe.Invoice.default_source",
        # InvoiceItem: pre-Price era invoice items may have no price
        "djstripe.InvoiceItem.price",
        # PaymentIntent: optional / Connect-only
        "djstripe.PaymentIntent.on_behalf_of",
        "djstripe.PaymentIntent.payment_method",
        "djstripe.PaymentIntent.upcominginvoice (related name)",
        # Product
        "djstripe.Product.default_price",
        # Subscription: optional defaults + scheduling
        "djstripe.Subscription.default_payment_method",
        "djstripe.Subscription.default_source",
        "djstripe.Subscription.pending_setup_intent",
        "djstripe.Subscription.schedule",
    }
)


class AssertStripeFksMixin:
    def _get_field_str(self, field) -> str:
        if isinstance(field, models.OneToOneRel):
            if field.parent_link:
                return ""
            reverse_id_name = str(field.remote_field.foreign_related_fields[0])
            return (
                reverse_id_name.replace("djstripe_id", field.name) + " (related name)"
            )

        if isinstance(field, models.ForeignKey):
            return str(field)

        return ""

    def assert_fks(
        self,
        obj,
        expected_blank_fks=frozenset(),
        processed_stripe_ids=None,
        optional_fks=COMMON_BLANK_FKS,
    ):
        """Recursively walk obj's foreign keys, asserting their nullness.

        - ``expected_blank_fks``: fields that *must* be None in this scenario.
        - ``optional_fks``: fields that *may* be None (defaults to the suite
          allowlist). For these, the value can be either set or unset — the
          assertion is skipped. If set, the FK is still walked recursively.
        - Anything not in either set must be non-None.
        """
        if processed_stripe_ids is None:
            processed_stripe_ids = set()

        processed_stripe_ids.add(obj.id)

        for field in obj._meta.get_fields():
            field_str = self._get_field_str(field)
            if not field_str or field_str.endswith(".djstripe_owner_account"):
                continue

            try:
                field_value = getattr(obj, field.name)
            except ObjectDoesNotExist:
                field_value = None

            if field_str in expected_blank_fks:
                self.assertIsNone(field_value, field_str)
                continue

            if field_value is None:
                # Optional fields are allowed to be missing; otherwise fail.
                if field_str not in optional_fks:
                    self.assertIsNotNone(field_value, field_str)
                continue

            # Field is populated — recurse into it.
            if field_value.id not in processed_stripe_ids:
                self.assert_fks(
                    field_value,
                    expected_blank_fks,
                    processed_stripe_ids,
                    optional_fks=optional_fks,
                )
