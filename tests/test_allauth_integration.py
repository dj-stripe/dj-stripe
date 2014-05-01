from django import forms
from django.test import TestCase


class TestAllAuthIntegration(TestCase):
    def test_import_signup_form(self):
        from djstripe.forms import StripeSubscriptionSignupForm
        self.assertIsInstance(StripeSubscriptionSignupForm(), forms.Form)
