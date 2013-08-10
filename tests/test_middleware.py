import datetime
import decimal

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from djstripe.models import Customer, CurrentSubscription
from djstripe import middleware
from djstripe.settings import User


class Request(object):

    def __init__(self, user, path):
        self.user = user
        self.path = path


class MiddlewareTest(TestCase):
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
            quantity=1
        )
        self.spm = middleware.SubscriptionPaymentMiddleware()

    def test_anonymous(self):
        request = Request(AnonymousUser(), "clarg")
        response = self.spm.process_request(request)
        self.assertEqual(response, None)

    def test_is_staff(self):
        self.user.is_staff = True
        self.user.save()
        request = Request(self.user, "nonsense")
        response = self.spm.process_request(request)
        self.assertEqual(response, None)

    def test_appname_exempt(self):
        request = Request(self.user, "/admin/")
        response = self.spm.process_request(request)
        self.assertEqual(response, None)

    def test_namespace_exempt(self):
        request = Request(self.user, "/djstripe/")
        response = self.spm.process_request(request)
        self.assertEqual(response, None)
