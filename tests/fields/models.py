"""Models used exclusively for testing"""

from django.db import models

from djstripe.fields import StripePercentField
from djstripe.models import StripeModel


class ExampleDecimalModel(models.Model):
    noval = StripePercentField()


class TestCustomActionModel(StripeModel):
    # for some reason having a FK here throws relation doesn't exist even though
    # djstripe is also one of the installed apps in tests.settings
    djstripe_owner_account = None
