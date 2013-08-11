import datetime
import sys

from django.contrib.auth.models import User, AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone

from djstripe.decorators import subscription_payment_required
from djstripe.models import Customer

PY3 = sys.version > '3'
if PY3:
    from unittest.mock import Mock
else:
    from mock import Mock

class TestSubscriptionPaymentRequired(TestCase):
    urls = 'tests.test_urls'

    def setUp(self):
        self.factory = RequestFactory()
    
    def test_anonymous(self):
        
        @subscription_payment_required
        def a_view(request):
            return HttpResponse()

        request = self.factory.get('/account/')
        request.user = AnonymousUser()
        self.assertRaises(ImproperlyConfigured, a_view, request)
        

    def test_user_unpaid(self):
        
        # create customer object with no subscription
        period_start = datetime.datetime(2013, 4, 1, tzinfo=timezone.utc)
        period_end = datetime.datetime(2013, 4, 30, tzinfo=timezone.utc)
        start = datetime.datetime(2013, 1, 1, tzinfo=timezone.utc)
        user = User.objects.create_user(username="pydanny")
        customer = Customer.objects.create(
            user=user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )
        
        @subscription_payment_required
        def a_view(request):
            return HttpResponse()

        request = self.factory.get('/account/')
        request.user = user
        
        response = a_view(request)
        self.assertEqual(response.status_code, 302)
