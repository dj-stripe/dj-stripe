import datetime
import decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.utils import timezone

from djstripe.models import Customer, Subscription
from djstripe.middleware import SubscriptionPaymentMiddleware


class MiddlewareURLTest(TestCase):

    def setUp(self):
        self.settings(ROOT_URLCONF='tests.test_urls')
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(username="pydanny",
                                                         email="pydanny@gmail.com")
        self.middleware = SubscriptionPaymentMiddleware()

    def test_appname(self):
        request = self.factory.get("/admin/")
        request.user = self.user

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_namespace(self):
        request = self.factory.get("/djstripe/")
        request.user = self.user

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_namespace_and_url(self):
        request = self.factory.get("/testapp_namespaced/")
        request.user = self.user

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_url(self):
        request = self.factory.get("/testapp/")
        request.user = self.user

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    @override_settings(DEBUG=True)
    def test_djdt(self):
        request = self.factory.get("/__debug__/")
        request.user = self.user

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)


class MiddlewareLogicTest(TestCase):
    urls = 'tests.test_urls'

    def setUp(self):
        period_start = datetime.datetime(2013, 4, 1, tzinfo=timezone.utc)
        period_end = datetime.datetime(2013, 4, 30, tzinfo=timezone.utc)
        start = datetime.datetime(2013, 1, 1, tzinfo=timezone.utc)

        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(username="pydanny",
                                                         email="pydanny@gmail.com")
        self.customer = Customer.objects.create(
            subscriber=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )
        self.subscription = Subscription.objects.create(
            stripe_id="sub_xxxxxxxxxxxxxxx",
            customer=self.customer,
            plan="test",
            current_period_start=period_start,
            current_period_end=period_end,
            amount=(500 / decimal.Decimal("100.0")),
            status="active",
            start=start,
            quantity=1,
            cancel_at_period_end=True
        )
        self.middleware = SubscriptionPaymentMiddleware()

    def test_anonymous(self):
        request = self.factory.get("/djstripe/")
        request.user = AnonymousUser()

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_is_staff(self):
        self.user.is_staff = True
        self.user.save()

        request = self.factory.get("/djstripe/")
        request.user = self.user

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_is_superuser(self):
        self.user.is_superuser = True
        self.user.save()

        request = self.factory.get("/djstripe/")
        request.user = self.user

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_customer_has_inactive_subscription(self):
        request = self.factory.get("/testapp_content/")
        request.user = self.user

        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 302)

    def test_customer_has_active_subscription(self):
        end_date = datetime.datetime(2100, 4, 30, tzinfo=timezone.utc)
        self.subscription.current_period_end = end_date
        self.subscription.save()

        request = self.factory.get("/testapp_content/")
        request.user = self.user

        response = self.middleware.process_request(request)
        self.assertEqual(response, None)
