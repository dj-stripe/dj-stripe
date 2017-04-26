"""
.. module:: dj-stripe.tests.test_settings
   :synopsis: dj-stripe Settings Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

"""

from django.core.exceptions import ImproperlyConfigured
from django.db.models.base import ModelBase
from django.test import TestCase
from django.test.utils import override_settings
from mock import patch

from djstripe import settings as djstripe_settings
from djstripe.settings import get_api_version, get_callback_function, get_subscriber_model


class TestSubscriberModelRetrievalMethod(TestCase):

    def test_with_user(self):
        user_model = get_subscriber_model()
        self.assertTrue(isinstance(user_model, ModelBase))

    @override_settings(
        DJSTRIPE_SUBSCRIBER_MODEL='testapp.Organization',
        DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK=(lambda request: request.org)
    )
    def test_with_org(self):
        org_model = get_subscriber_model()
        self.assertTrue(isinstance(org_model, ModelBase))

    @override_settings(
        DJSTRIPE_SUBSCRIBER_MODEL='testapp.StaticEmailOrganization',
        DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK=(lambda request: request.org)
    )
    def test_with_org_static(self):
        org_model = get_subscriber_model()
        self.assertTrue(isinstance(org_model, ModelBase))

    @override_settings(
        DJSTRIPE_SUBSCRIBER_MODEL='testappStaticEmailOrganization',
        DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK=(lambda request: request.org)
    )
    def test_bad_model_name(self):
        self.assertRaisesMessage(
            ImproperlyConfigured,
            "DJSTRIPE_SUBSCRIBER_MODEL must be of the form 'app_label.model_name'.",
            get_subscriber_model
        )

    @override_settings(
        DJSTRIPE_SUBSCRIBER_MODEL='testapp.UnknownModel',
        DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK=(lambda request: request.org)
    )
    def test_unknown_model(self):
        self.assertRaisesMessage(
            ImproperlyConfigured,
            "DJSTRIPE_SUBSCRIBER_MODEL refers to model 'testapp.UnknownModel' that has not been installed.",
            get_subscriber_model
        )

    @override_settings(
        DJSTRIPE_SUBSCRIBER_MODEL='testapp.NoEmailOrganization',
        DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK=(lambda request: request.org)
    )
    def test_no_email_model(self):
        self.assertRaisesMessage(
            ImproperlyConfigured,
            "DJSTRIPE_SUBSCRIBER_MODEL must have an email attribute.",
            get_subscriber_model
        )

    @override_settings(DJSTRIPE_SUBSCRIBER_MODEL='testapp.Organization')
    def test_no_callback(self):
        self.assertRaisesMessage(
            ImproperlyConfigured,
            "DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK must be implemented if a DJSTRIPE_SUBSCRIBER_MODEL is "
            "defined.",
            get_subscriber_model
        )

    @override_settings(DJSTRIPE_SUBSCRIBER_MODEL='testapp.Organization', DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK=5)
    def test_bad_callback(self):
        self.assertRaisesMessage(
            ImproperlyConfigured,
            "DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK must be callable.",
            get_subscriber_model
        )

    @override_settings(DJSTRIPE_TEST_CALLBACK=(lambda: "ok"))
    def test_get_callback_function_with_valid_func_callable(self):
        func = get_callback_function("DJSTRIPE_TEST_CALLBACK")
        self.assertEquals("ok", func())

    @override_settings(DJSTRIPE_TEST_CALLBACK='foo.valid_callback')
    @patch.object(djstripe_settings, 'import_string', return_value=(lambda: "ok"))
    def test_get_callback_function_with_valid_string_callable(self, import_string_mock):
        func = get_callback_function("DJSTRIPE_TEST_CALLBACK")
        self.assertEquals("ok", func())
        import_string_mock.assert_called_with('foo.valid_callback')

    @override_settings(DJSTRIPE_TEST_CALLBACK='foo.non_existant_callback')
    def test_get_callback_function_import_error(self):
        with self.assertRaises(ImportError):
            get_callback_function("DJSTRIPE_TEST_CALLBACK")

    @override_settings(DJSTRIPE_TEST_CALLBACK='foo.invalid_callback')
    @patch.object(djstripe_settings, 'import_string', return_value="not_callable")
    def test_get_callback_function_with_non_callable_string(self, import_string_mock):
        with self.assertRaises(ImproperlyConfigured):
            get_callback_function("DJSTRIPE_TEST_CALLBACK")
        import_string_mock.assert_called_with('foo.invalid_callback')

    @override_settings(DJSTRIPE_TEST_CALLBACK='foo.non_existant_callback')
    def test_get_callback_function_(self):
        with self.assertRaises(ImportError):
            get_callback_function("DJSTRIPE_TEST_CALLBACK")


class TestGetApiVersion(TestCase):

    @override_settings(DJSTRIPE_API_VERSION=None)
    def test_with_default(self):
        self.assertEquals('2017-02-14', get_api_version())

    @override_settings(DJSTRIPE_API_VERSION='latest')
    def test_with_latest(self):
        self.assertIsNone(get_api_version())

    @override_settings(DJSTRIPE_API_VERSION='2016-03-07')
    def test_with_valid_date(self):
        self.assertEquals('2016-03-07', get_api_version())

    @override_settings(DJSTRIPE_API_VERSION='foobar')
    def test_with_invalid_date(self):
        err = 'must be a valid date'
        with self.assertRaisesRegexp(ImproperlyConfigured, err):
            get_api_version()
