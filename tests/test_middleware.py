"""
.. module:: dj-stripe.tests.test_middleware
   :synopsis: dj-stripe Middleware Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings

from djstripe.middleware import SubscriptionPaymentMiddleware
from djstripe.models import Customer, Subscription
from tests import FAKE_SUBSCRIPTION, FUTURE_DATE, FAKE_CUSTOMER


class MiddlewareURLTest(TestCase):
    urlconf = 'tests.test_urls'

    def setUp(self):
        self.settings(ROOT_URLCONF=self.urlconf)
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        self.middleware = SubscriptionPaymentMiddleware()

    def test_appname(self):
        request = self.factory.get("/admin/")
        request.user = self.user
        request.urlconf = self.urlconf

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_namespace(self):
        request = self.factory.get("/djstripe/webhook/")
        request.user = self.user
        request.urlconf = self.urlconf

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_namespace_and_url(self):
        request = self.factory.get("/testapp_namespaced/")
        request.user = self.user
        request.urlconf = self.urlconf

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_url(self):
        request = self.factory.get("/testapp/")
        request.user = self.user
        request.urlconf = self.urlconf

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    @override_settings(DEBUG=True)
    def test_djdt(self):
        request = self.factory.get("/__debug__/")
        request.user = self.user
        request.urlconf = self.urlconf

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_fnmatch(self):
        request = self.factory.get("/test_fnmatch/extra_text/")
        request.user = self.user
        request.urlconf = self.urlconf

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)


class MiddlewareLogicTest(TestCase):
    urlconf = 'tests.test_urls'

    def setUp(self):
        self.settings(ROOT_URLCONF=self.urlconf)
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        self.customer = Customer.objects.create(subscriber=self.user, stripe_id=FAKE_CUSTOMER["id"], livemode=False)
        self.subscription = Subscription.sync_from_stripe_data(FAKE_SUBSCRIPTION)
        self.middleware = SubscriptionPaymentMiddleware()

    def test_anonymous(self):
        request = self.factory.get("/djstripe/webhook/")
        request.user = AnonymousUser()
        request.urlconf = self.urlconf

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_is_staff(self):
        self.user.is_staff = True
        self.user.save()

        request = self.factory.get("/djstripe/webhook/")
        request.user = self.user
        request.urlconf = self.urlconf

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_is_superuser(self):
        self.user.is_superuser = True
        self.user.save()

        request = self.factory.get("/djstripe/webhook/")
        request.user = self.user
        request.urlconf = self.urlconf

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_customer_has_inactive_subscription(self):
        request = self.factory.get("/testapp_content/")
        request.user = self.user
        request.urlconf = self.urlconf

        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 302)

    def test_customer_has_active_subscription(self):
        self.subscription.current_period_end = FUTURE_DATE
        self.subscription.save()

        request = self.factory.get("/testapp_content/")
        request.user = self.user
        request.urlconf = self.urlconf

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)
