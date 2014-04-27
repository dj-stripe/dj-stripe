from django.test import TestCase
from django.test.client import RequestFactory
from django.core.exceptions import ImproperlyConfigured
from django.test.utils import override_settings

from djstripe.settings import User
from djstripe.models import Customer
from djstripe.plugins.default import DefaultPlugin
from djstripe.plugins import get_plugin
from djstripe import settings

class BackendRetrievalTests(TestCase):
    """
    Test that utilities for retrieving the active plugin work
    properly.

    """
    def test_get_plugin(self):
        """
        Verify that ``get_plugin()`` returns the correct value when
        passed a valid plugin.

        """
        self.failUnless(isinstance(get_plugin(),
                                   DefaultPlugin))




class TestUserBackend(TestCase):
    #TODO:
    #Add more tests!
    def setUp(self):
        self.user = User.objects.create_user(username="pydanny")        
        self.customer = Customer.objects.create(
            related_model=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )
        self.plugin = get_plugin()
        self.factory = RequestFactory()
        self.request = self.factory.get('/account/')
        self.request.user = self.user        
        
    def test_get_customer(self):
        customer = self.plugin.get_customer(self.request)        
        self.assertTrue(isinstance(customer, Customer))

        
   