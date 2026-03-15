import stripe
from django.db import models

from ..fields import StripeForeignKey
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


class ProductFeature(StripeModel):
    """
    A product_feature represents a feature attached to a product.
    When a product is purchased that has a feature, Stripe will create
    an entitlement to that feature for the purchasing customer.

    Stripe Documentation: https://stripe.com/docs/api/product-feature
    """

    stripe_class = stripe.ProductFeature

    product = StripeForeignKey(
        "Product",
        on_delete=models.CASCADE,
        related_name="features",
        help_text="The product this feature is attached to.",
    )
    entitlement_feature = StripeForeignKey(
        "Feature",
        on_delete=models.CASCADE,
        related_name="product_features",
        help_text="The feature that this product feature references.",
    )


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
