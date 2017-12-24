from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings

from djstripe import settings as djstripe_settings
from djstripe.models import StripeObject
from djstripe.settings import KEYS, get_keymanager

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
        self.assertEqual(djstripe_settings.STRIPE_LIVE_MODE, True)
        self.assertEqual(KEYS.STRIPE_SECRET_KEY, "sk_live_foo")
        # self.assertEqual(djstripe_settings.LIVE_API_KEY, "sk_live_foo")
        self.assertEqual(self.live_object.default_api_key, "sk_live_foo")

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_foo",
        STRIPE_PUBLIC_KEY="pk_test_foo",
        STRIPE_LIVE_MODE=False
    )
    def test_global_api_keys_test_mode(self):
        reload(djstripe_settings)
        self.assertEqual(djstripe_settings.STRIPE_LIVE_MODE, False)
        self.assertEqual(KEYS.STRIPE_SECRET_KEY, "sk_test_foo")
        # self.assertEqual(djstripe_settings.TEST_API_KEY, "sk_test_foo")
        self.assertEqual(self.test_object.default_api_key, "sk_test_foo")

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
        self.assertEqual(djstripe_settings.STRIPE_LIVE_MODE, True)
        self.assertEqual(KEYS.STRIPE_SECRET_KEY, "sk_live_foo")
        self.assertEqual(KEYS.STRIPE_PUBLIC_KEY, "pk_live_foo")
        self.assertEqual(KEYS.LIVE_SECRET_KEY, "sk_live_foo")
        self.assertEqual(self.live_object.default_api_key, "sk_live_foo")

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
        self.assertEqual(djstripe_settings.STRIPE_LIVE_MODE, False)
        self.assertEqual(KEYS.STRIPE_SECRET_KEY, "sk_test_foo")
        self.assertEqual(KEYS.STRIPE_PUBLIC_KEY, "pk_test_foo")
        self.assertEqual(KEYS.TEST_SECRET_KEY, "sk_test_foo")
        self.assertEqual(self.test_object.default_api_key, "sk_test_foo")

    def test_improper_configuration1(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            get_keymanager('doesn.not.exists')
        self.assertEqual(
            str(ctx.exception),
            'DJSTRIPE_KEYMANAGER_CLASS is not set properly. doesn.not.exists isn\'t found'
        )

    def test_improper_configuration2(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            get_keymanager('djstripe.settings.NotExists')
        self.assertEqual(
            str(ctx.exception),
            'DJSTRIPE_KEYMANAGER_CLASS is not set properly. djstripe.settings.NotExists isn\'t found'
        )

    def test_improper_configuration3(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            get_keymanager('djstripe.settings.get_callback_function')
        self.assertEqual(str(ctx.exception), 'DJSTRIPE_KEYMANAGER_CLASS must be string or class.')

    def tearDown(self):
        reload(djstripe_settings)
