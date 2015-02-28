from django.test import TestCase

from djstripe.context_processors import djstripe_settings
from djstripe import settings


class TestContextProcessor(TestCase):

    def test_results(self):
        ctx = djstripe_settings(None)
        self.assertEquals(ctx["STRIPE_PUBLIC_KEY"], settings.STRIPE_PUBLIC_KEY)
