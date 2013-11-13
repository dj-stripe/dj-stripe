import datetime
import decimal

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.utils import timezone

from djstripe.settings import User
from djstripe.models import convert_tstamp, Customer, CurrentSubscription
from djstripe.utils import user_has_active_subscription


class TestTimestampConversion(TestCase):

    def test_conversion_without_field_name(self):
        stamp = convert_tstamp(1365567407)
        self.assertEquals(
            stamp,
            datetime.datetime(2013, 4, 10, 4, 16, 47, tzinfo=timezone.utc)
        )

    def test_conversion_with_field_name(self):
        stamp = convert_tstamp({"my_date": 1365567407}, "my_date")
        self.assertEquals(
            stamp,
            datetime.datetime(2013, 4, 10, 4, 16, 47, tzinfo=timezone.utc)
        )

    def test_conversion_with_invalid_field_name(self):
        stamp = convert_tstamp({"my_date": 1365567407}, "foo")
        self.assertEquals(
            stamp,
            None
        )


class TestUserHasActiveSubscription(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="pydanny")
        self.customer = Customer.objects.create(
            user=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )

    def test_user_has_inactive_subscription(self):
        self.assertFalse(user_has_active_subscription(self.user))

    def test_user_has_active_subscription(self):
        # Make the user have an active subscription
        period_start = datetime.datetime(2013, 4, 1, tzinfo=timezone.utc)
        period_end = datetime.datetime(2013, 4, 30, tzinfo=timezone.utc)

        # Start 'em off'
        start = datetime.datetime(2013, 1, 1, 0, 0, 1)  # more realistic start
        CurrentSubscription.objects.create(
            customer=self.customer,
            plan="test",
            current_period_start=period_start,
            current_period_end=period_end,
            amount=(500 / decimal.Decimal("100.0")),
            status="active",
            start=start,
            quantity=1
        )

        # Assert that the user's subscription is action
        self.assertTrue(user_has_active_subscription(self.user))

    def test_anonymous_user(self):
        """ This needs to throw an ImproperlyConfigured error so the developer
            can be guided to properly protect the subscription content.
        """
        anon_user = AnonymousUser()
        with self.assertRaises(ImproperlyConfigured):
            user_has_active_subscription(anon_user)
