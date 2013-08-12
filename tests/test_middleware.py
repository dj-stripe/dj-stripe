import datetime
import decimal

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone


from djstripe.models import Customer, CurrentSubscription
from djstripe import middleware
from djstripe.settings import User


class Request(object):
    # TODO - Switch to RequestFactory

    def __init__(self, user, path):
        self.user = user
        self.path = path


class MiddlewareURLTest(TestCase):
    urls = 'tests.test_urls'

    def setUp(self):
        self.user = User.objects.create_user(username="pydanny")
        self.middleware = middleware.SubscriptionPaymentMiddleware()

    def test_appname(self):
        request = Request(self.user, "/admin/")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_namespace(self):
        request = Request(self.user, "/djstripe/")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_namespace_and_url(self):
        request = Request(self.user, "/testapp_namespaced/")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_url(self):
        request = Request(self.user, "/testapp/")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)


class MiddlewareLogicTest(TestCase):
    urls = 'tests.test_urls'

    def setUp(self):
        period_start = datetime.datetime(2013, 4, 1, tzinfo=timezone.utc)
        period_end = datetime.datetime(2013, 4, 30, tzinfo=timezone.utc)
        start = datetime.datetime(2013, 1, 1, tzinfo=timezone.utc)
        self.user = User.objects.create_user(username="pydanny")
        self.customer = Customer.objects.create(
            user=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )
        self.subscription = CurrentSubscription.objects.create(
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
        self.middleware = middleware.SubscriptionPaymentMiddleware()

    def test_anonymous(self):
        request = Request(AnonymousUser(), "clarg")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_is_staff(self):
        self.user.is_staff = True
        self.user.save()
        request = Request(self.user, "nonsense")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)

    def test_customer_has_inactive_subscription(self):
        request = Request(self.user, "/testapp_content/")
        response = self.middleware.process_request(request)
        self.assertEqual(response.status_code, 302)

    def test_customer_has_active_subscription(self):
        end_date = datetime.datetime(2100, 4, 30, tzinfo=timezone.utc)
        self.subscription.current_period_end = end_date
        self.subscription.save()
        request = Request(self.user, "/testapp_content/")
        response = self.middleware.process_request(request)
        self.assertEqual(response, None)
