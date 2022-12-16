"""
dj-stripe Settings Tests.
"""
from unittest.mock import patch

import stripe
from django.core.exceptions import ImproperlyConfigured
from django.db.models.base import ModelBase
from django.test import TestCase
from django.test.utils import override_settings

from djstripe import settings


class TestSubscriberModelRetrievalMethod(TestCase):
    def test_with_user(self):
        user_model = settings.djstripe_settings.get_subscriber_model()
        self.assertTrue(isinstance(user_model, ModelBase))

    @override_settings(
        DJSTRIPE_SUBSCRIBER_MODEL="testapp.Organization",
        DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK=(lambda request: request.org),
    )
    def test_with_org(self):
        org_model = settings.djstripe_settings.get_subscriber_model()
        self.assertTrue(isinstance(org_model, ModelBase))

    @override_settings(
        DJSTRIPE_SUBSCRIBER_MODEL="testapp.StaticEmailOrganization",
        DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK=(lambda request: request.org),
    )
    def test_with_org_static(self):
        org_model = settings.djstripe_settings.get_subscriber_model()
        self.assertTrue(isinstance(org_model, ModelBase))

    @override_settings(
        DJSTRIPE_SUBSCRIBER_MODEL="testappStaticEmailOrganization",
        DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK=(lambda request: request.org),
    )
    def test_bad_model_name(self):
        self.assertRaisesMessage(
            ImproperlyConfigured,
            "DJSTRIPE_SUBSCRIBER_MODEL must be of the form 'app_label.model_name'.",
            settings.djstripe_settings.get_subscriber_model,
        )

    @override_settings(
        DJSTRIPE_SUBSCRIBER_MODEL="testapp.UnknownModel",
        DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK=(lambda request: request.org),
    )
    def test_unknown_model(self):
        self.assertRaisesMessage(
            ImproperlyConfigured,
            "DJSTRIPE_SUBSCRIBER_MODEL refers to model 'testapp.UnknownModel' "
            "that has not been installed.",
            settings.djstripe_settings.get_subscriber_model,
        )

    @override_settings(
        DJSTRIPE_SUBSCRIBER_MODEL="testapp.NoEmailOrganization",
        DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK=(lambda request: request.org),
    )
    def test_no_email_model(self):
        self.assertRaisesMessage(
            ImproperlyConfigured,
            "DJSTRIPE_SUBSCRIBER_MODEL must have an email attribute.",
            settings.djstripe_settings.get_subscriber_model,
        )

    @override_settings(DJSTRIPE_SUBSCRIBER_MODEL="testapp.Organization")
    def test_no_callback(self):
        self.assertRaisesMessage(
            ImproperlyConfigured,
            "DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK must be implemented "
            "if a DJSTRIPE_SUBSCRIBER_MODEL is defined.",
            settings.djstripe_settings.get_subscriber_model,
        )

    @override_settings(
        DJSTRIPE_SUBSCRIBER_MODEL="testapp.Organization",
        DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK=5,
    )
    def test_bad_callback(self):
        self.assertRaisesMessage(
            ImproperlyConfigured,
            "DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK must be callable.",
            settings.djstripe_settings.get_subscriber_model,
        )

    @override_settings(DJSTRIPE_TEST_CALLBACK=(lambda: "ok"))
    def test_get_callback_function_with_valid_func_callable(self):
        func = settings.djstripe_settings.get_callback_function(
            "DJSTRIPE_TEST_CALLBACK"
        )
        self.assertEqual("ok", func())

    @override_settings(DJSTRIPE_TEST_CALLBACK="foo.valid_callback")
    @patch.object(settings, "import_string", return_value=(lambda: "ok"))
    def test_get_callback_function_with_valid_string_callable(self, import_string_mock):
        func = settings.djstripe_settings.get_callback_function(
            "DJSTRIPE_TEST_CALLBACK"
        )
        self.assertEqual("ok", func())
        import_string_mock.assert_called_with("foo.valid_callback")

    @override_settings(DJSTRIPE_TEST_CALLBACK="foo.non_existant_callback")
    def test_get_callback_function_import_error(self):
        with self.assertRaises(ImportError):
            settings.djstripe_settings.get_callback_function("DJSTRIPE_TEST_CALLBACK")

    @override_settings(DJSTRIPE_TEST_CALLBACK="foo.invalid_callback")
    @patch.object(settings, "import_string", return_value="not_callable")
    def test_get_callback_function_with_non_callable_string(self, import_string_mock):
        with self.assertRaises(ImproperlyConfigured):
            settings.djstripe_settings.get_callback_function("DJSTRIPE_TEST_CALLBACK")
        import_string_mock.assert_called_with("foo.invalid_callback")

    @override_settings(DJSTRIPE_TEST_CALLBACK="foo.non_existant_callback")
    def test_get_callback_function_(self):
        with self.assertRaises(ImportError):
            settings.djstripe_settings.get_callback_function("DJSTRIPE_TEST_CALLBACK")


@override_settings(STRIPE_API_VERSION=None)
class TestGetStripeApiVersion(TestCase):
    def test_with_default(self):
        self.assertEqual(
            settings.djstripe_settings.DEFAULT_STRIPE_API_VERSION,
            settings.djstripe_settings.STRIPE_API_VERSION,
        )

    @override_settings(STRIPE_API_VERSION="2016-03-07")
    def test_with_override(self):
        self.assertEqual(
            "2016-03-07",
            settings.djstripe_settings.STRIPE_API_VERSION,
        )


class TestObjectPatching(TestCase):
    @patch.object(
        settings.djstripe_settings,
        "DJSTRIPE_WEBHOOK_URL",
        return_value=r"^webhook/sample/$",
    )
    def test_object_patching(self, mock):
        webhook_url = settings.djstripe_settings.DJSTRIPE_WEBHOOK_URL
        self.assertTrue(webhook_url, r"^webhook/sample/$")
