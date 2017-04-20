from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from djstripe import settings as djstripe_settings
from djstripe.stripe_objects import StripeObject

try:
    reload
except NameError:
    from importlib import reload


class TestSubscriberModelRetrievalMethod(TestCase):
    def setUp(self):
        self.live_object = StripeObject(livemode=True)
        self.test_object = StripeObject(livemode=False)
        self.unk_object = StripeObject(livemode=None)

    @override_settings(
        STRIPE_SECRET_KEY="sk_live_foo",
        STRIPE_PUBLIC_KEY="pk_live_foo",
        STRIPE_LIVE_MODE=True
    )
    def test_global_api_keys_live_mode(self):
        reload(djstripe_settings)
        self.assertEquals(djstripe_settings.STRIPE_LIVE_MODE, True)
        self.assertEquals(djstripe_settings.STRIPE_SECRET_KEY, "sk_live_foo")
        # self.assertEquals(djstripe_settings.LIVE_API_KEY, "sk_live_foo")
        self.assertEquals(self.live_object.default_api_key, "sk_live_foo")

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_foo",
        STRIPE_PUBLIC_KEY="pk_test_foo",
        STRIPE_LIVE_MODE=False
    )
    def test_global_api_keys_test_mode(self):
        reload(djstripe_settings)
        self.assertEquals(djstripe_settings.STRIPE_LIVE_MODE, False)
        self.assertEquals(djstripe_settings.STRIPE_SECRET_KEY, "sk_test_foo")
        # self.assertEquals(djstripe_settings.TEST_API_KEY, "sk_test_foo")
        self.assertEquals(self.test_object.default_api_key, "sk_test_foo")

    @override_settings(
        STRIPE_TEST_SECRET_KEY="sk_test_foo",
        STRIPE_LIVE_SECRET_KEY="sk_live_foo",
        STRIPE_TEST_PUBLIC_KEY="pk_test_foo",
        STRIPE_LIVE_PUBLIC_KEY="pk_live_foo",
        STRIPE_LIVE_MODE=True,
    )
    def test_api_key_live_mode(self):
        del settings.STRIPE_SECRET_KEY
        del settings.STRIPE_PUBLIC_KEY
        reload(djstripe_settings)
        self.assertEquals(djstripe_settings.STRIPE_LIVE_MODE, True)
        self.assertEquals(djstripe_settings.STRIPE_SECRET_KEY, "sk_live_foo")
        self.assertEquals(djstripe_settings.STRIPE_PUBLIC_KEY, "pk_live_foo")
        self.assertEquals(djstripe_settings.LIVE_API_KEY, "sk_live_foo")
        self.assertEquals(self.live_object.default_api_key, "sk_live_foo")

    @override_settings(
        STRIPE_TEST_SECRET_KEY="sk_test_foo",
        STRIPE_LIVE_SECRET_KEY="sk_live_foo",
        STRIPE_TEST_PUBLIC_KEY="pk_test_foo",
        STRIPE_LIVE_PUBLIC_KEY="pk_live_foo",
        STRIPE_LIVE_MODE=False,
    )
    def test_secret_key_test_mode(self):
        del settings.STRIPE_SECRET_KEY
        del settings.STRIPE_PUBLIC_KEY
        reload(djstripe_settings)
        self.assertEquals(djstripe_settings.STRIPE_LIVE_MODE, False)
        self.assertEquals(djstripe_settings.STRIPE_SECRET_KEY, "sk_test_foo")
        self.assertEquals(djstripe_settings.STRIPE_PUBLIC_KEY, "pk_test_foo")
        self.assertEquals(djstripe_settings.TEST_API_KEY, "sk_test_foo")
        self.assertEquals(self.test_object.default_api_key, "sk_test_foo")

    def tearDown(self):
        reload(djstripe_settings)
