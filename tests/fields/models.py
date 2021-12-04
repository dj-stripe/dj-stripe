"""Models used exclusively for testing"""

from django.db import models

from djstripe.fields import StripePercentField


class TestDecimalModel(models.Model):
    noval = StripePercentField()
