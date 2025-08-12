import stripe

from .base import StripeModel


class Feature(StripeModel):
    """
    A feature represents a monetizable ability or functionality in your system.
    Features can be assigned to products, and when those products are purchased,
    Stripe will create an entitlement to the feature for the purchasing customer.

    Stirpe Documentation: https://stripe.com/docs/api/entitlements/feature
    """

    stripe_class = stripe.entitlements.Feature

    # https://docs.stripe.com/api/entitlements/feature/object#entitlements_feature_object-lookup_key
    @property
    def lookup_key(self) -> str:
        return self.stripe_data["lookup_key"]

    # https://docs.stripe.com/api/entitlements/feature/object#entitlements_feature_object-name
    @property
    def name(self) -> str:
        return self.stripe_data["name"]


class ActiveEntitlement(StripeModel):
    """
    An active entitlement describes access to a feature for a customer.

    Stirpe Documentation: https://stripe.com/docs/api/entitlements/active_entitlement
    """

    stripe_class = stripe.entitlements.ActiveEntitlement

    # https://docs.stripe.com/api/entitlements/active-entitlement/object#entitlements_active_entitlement_object-lookup_key
    @property
    def lookup_key(self) -> str:
        return self.stripe_data["lookup_key"]
