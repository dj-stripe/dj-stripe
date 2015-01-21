import datetime
import decimal

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from djstripe.models import convert_tstamp, DJStripeCustomer, CurrentSubscription
from djstripe.utils import customer_has_active_subscription


class TestDeprecationWarning(TestCase):
    """
    Tests the deprecation warning set in the decorators file.
    See https://docs.python.org/3.4/library/warnings.html#testing-warnings
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pydanny",
                                                         email="pydanny@gmail.com")
        self.djstripecustomer = DJStripeCustomer.objects.create(
            customer=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )

    def test_deprecation(self):
        with self.assertWarns(DeprecationWarning):
            from djstripe.utils import user_has_active_subscription
            user_has_active_subscription(self.user)


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

    @override_settings(USE_TZ=False)
    def test_conversion_without_field_name_no_tz(self):
        stamp = convert_tstamp(1365567407)
        self.assertEquals(
            stamp,
            datetime.datetime(2013, 4, 9, 21, 16, 47)
        )

    @override_settings(USE_TZ=False)
    def test_conversion_with_field_name_no_tz(self):
        stamp = convert_tstamp({"my_date": 1365567407}, "my_date")
        self.assertEquals(
            stamp,
            datetime.datetime(2013, 4, 9, 21, 16, 47)
        )

    @override_settings(USE_TZ=False)
    def test_conversion_with_invalid_field_name_no_tz(self):
        stamp = convert_tstamp({"my_date": 1365567407}, "foo")
        self.assertEquals(
            stamp,
            None
        )


class TestUserHasActiveSubscription(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pydanny",
                                                         email="pydanny@gmail.com")
        self.djstripecustomer = DJStripeCustomer.objects.create(
            customer=self.user,
            stripe_id="cus_xxxxxxxxxxxxxxx",
            card_fingerprint="YYYYYYYY",
            card_last_4="2342",
            card_kind="Visa"
        )

    def test_user_has_inactive_subscription(self):
        self.assertFalse(customer_has_active_subscription(self.user))

    def test_user_has_active_subscription(self):
        # Make the customer have an active subscription
        period_start = datetime.datetime(2013, 4, 1, tzinfo=timezone.utc)
        period_end = datetime.datetime(2013, 4, 30, tzinfo=timezone.utc)

        # Start 'em off'
        start = datetime.datetime(2013, 1, 1, 0, 0, 1)  # more realistic start
        CurrentSubscription.objects.create(
            djstripecustomer=self.djstripecustomer,
            plan="test",
            current_period_start=period_start,
            current_period_end=period_end,
            amount=(500 / decimal.Decimal("100.0")),
            status="active",
            start=start,
            quantity=1
        )

        # Assert that the customer's subscription is action
        self.assertTrue(customer_has_active_subscription(self.user))

    def test_anonymous_user(self):
        """
        This needs to throw an ImproperlyConfigured error so the developer
        can be guided to properly protect the subscription content.
        """
        anon_user = AnonymousUser()
        with self.assertRaises(ImproperlyConfigured):
            customer_has_active_subscription(anon_user)

    def test_staff_user(self):
        self.user.is_staff = True
        self.user.save()

        self.assertTrue(customer_has_active_subscription(self.user))

    def test_superuser(self):
        self.user.is_superuser = True
        self.user.save()

        self.assertTrue(customer_has_active_subscription(self.user))
