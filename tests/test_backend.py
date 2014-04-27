from django.test import TestCase
from django.test.client import RequestFactory
from django.core.exceptions import ImproperlyConfigured
from django.test.utils import override_settings

from djstripe.settings import User
from djstripe.models import Customer
from djstripe.backends.default import DefaultBackend
from djstripe.backends import get_backend
from djstripe import settings

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
        self.backend = get_backend()
        self.factory = RequestFactory()
        self.request = self.factory.get('/account/')
        self.request.user = self.user        
        
    def test_get_customer(self):
        customer = self.backend.get_customer(self.request)        
        self.assertTrue(isinstance(customer, Customer))

        
   