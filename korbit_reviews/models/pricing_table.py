from django.db import models

from ..fields import (
    StripeForeignKey,
)
from .base import StripeModel


class PricingTable(StripeModel):
    object = "pricing_table"

    active = models.BooleanField()
    merchant = StripeForeignKey("djstripe.Account", on_delete=models.CASCADE)
    merchant_internal_label = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.merchant_internal_label

    @property
    def items(self) -> list:
        return self.stripe_data.get("pricing_table_items", [])
