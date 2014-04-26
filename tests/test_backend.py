from django.test import TestCase
from django.test.client import RequestFactory
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.test.utils import override_settings

from djstripe.settings import User
from djstripe.models import Customer
from djstripe.backends.default import DefaultBackend
from djstripe.backends import get_backend


class BackendRetrievalTests(TestCase):
    """
    Test that utilities for retrieving the active backend work
    properly.

    """
    def test_get_backend(self):
        """
        Verify that ``get_backend()`` returns the correct value when
        passed a valid backend.

        """
        self.failUnless(isinstance(get_backend(),
                                   DefaultBackend))

    """
    @override_settings(DJSTRIPE_BACKEND='djstripe.backends.doesnotexist.NonExistentBackend')
    def test_backend_error_invalid(self):
        

        self.assertRaises(ImproperlyConfigured, get_backend)        
        
    

    @override_settings(DJSTRIPE_BACKEND='djstripe.backends.default.NonexistentBackend')
    def test_backend_attribute_error(self):
        
        Test that a backend module which exists but does not have a
        class of the specified name raises the correct exception.
        
        
        self.assertRaises(ImproperlyConfigured, get_backend)        

    """


class TestUserBackend(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(username="pydanny")        
        self.customer = Customer.objects.create(
            user=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )
        self.backend = get_backend()
        self.factory = RequestFactory()
        self.request = self.factory.get('/account/')
        self.request.user = self.user        
        
    def test_get_customer(self):
        customer = self.backend.get_customer(self.request)        
        self.assertTrue(isinstance(customer, Customer))
    
    """
    
    def test_successful_create_customer_from_user(self):
        pass
            
    def test_successful_create_customer(self):
        customer, created = self.backend.create_customer(self.request)        
        self.assertTrue(isinstance(customer, Customer))        
        self.assertFalse(created)        
        self.request.user = User.objects.create_user(username="msaizar")
        customer, created = self.backend.create_customer(self.request)
        self.assertTrue(isinstance(customer, Customer))
        self.assertTrue(created)
    """
        
   