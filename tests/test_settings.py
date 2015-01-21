from django.db.models.base import ModelBase
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings

from djstripe.settings import get_customer_model


class TestCustomerModelRetrievalMethod(TestCase):

    def test_with_user(self):
        user_model = get_customer_model()
        self.assertTrue(isinstance(user_model, ModelBase))

    @override_settings(DJSTRIPE_CUSTOMER_MODEL='testapp.Organization', DJSTRIPE_CUSTOMER_MODEL_REQUEST_CALLBACK=(lambda request: request.org))
    def test_with_org(self):
        org_model = get_customer_model()
        self.assertTrue(isinstance(org_model, ModelBase))

    @override_settings(DJSTRIPE_CUSTOMER_MODEL='testapp.StaticEmailOrganization', DJSTRIPE_CUSTOMER_MODEL_REQUEST_CALLBACK=(lambda request: request.org))
    def test_with_org_static(self):
        org_model = get_customer_model()
        self.assertTrue(isinstance(org_model, ModelBase))

    @override_settings(DJSTRIPE_CUSTOMER_MODEL='testappStaticEmailOrganization', DJSTRIPE_CUSTOMER_MODEL_REQUEST_CALLBACK=(lambda request: request.org))
    def test_bad_model_name(self):
        self.assertRaisesMessage(ImproperlyConfigured, "DJSTRIPE_CUSTOMER_MODEL must be of the form 'app_label.model_name'.", get_customer_model)

    @override_settings(DJSTRIPE_CUSTOMER_MODEL='testapp.UnknownModel', DJSTRIPE_CUSTOMER_MODEL_REQUEST_CALLBACK=(lambda request: request.org))
    def test_unknown_model(self):
        self.assertRaisesMessage(ImproperlyConfigured, "DJSTRIPE_CUSTOMER_MODEL refers to model 'testapp.UnknownModel' that has not been installed.", get_customer_model)

    @override_settings(DJSTRIPE_CUSTOMER_MODEL='testapp.NoEmailOrganization', DJSTRIPE_CUSTOMER_MODEL_REQUEST_CALLBACK=(lambda request: request.org))
    def test_no_email_model(self):
        self.assertRaisesMessage(ImproperlyConfigured, "DJSTRIPE_CUSTOMER_MODEL must have an email attribute.", get_customer_model)

    @override_settings(DJSTRIPE_CUSTOMER_MODEL='testapp.Organization')
    def test_no_callback(self):
        self.assertRaisesMessage(ImproperlyConfigured, "DJSTRIPE_CUSTOMER_MODEL_REQUEST_CALLBACK must be implemented if a DJSTRIPE_CUSTOMER_MODEL is defined.", get_customer_model)

    @override_settings(DJSTRIPE_CUSTOMER_MODEL='testapp.Organization', DJSTRIPE_CUSTOMER_MODEL_REQUEST_CALLBACK=5)
    def test_bad_callback(self):
        self.assertRaisesMessage(ImproperlyConfigured, "DJSTRIPE_CUSTOMER_MODEL_REQUEST_CALLBACK must be callable.", get_customer_model)
