"""Models used exclusively for testing"""

from django.db import models

from djstripe.fields import StripePercentField
from djstripe.models import StripeModel


class ExampleDecimalModel(models.Model):
    noval = StripePercentField()


class MockStripeClass:
    def retrieve(self):
        return self


class CustomActionModel(StripeModel):
    # for some reason having a FK here throws relation doesn't exist even though
    # djstripe is also one of the installed apps in tests.settings
    djstripe_owner_account = None
    stripe_class = MockStripeClass

    # For Subscription model's custom action, _cancel
    def cancel(self, at_period_end: bool = False, **kwargs):
        pass
