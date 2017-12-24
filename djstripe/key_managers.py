from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings


class DefaultKeyManager(object):
    @property
    def TEST_SECRET_KEY(self):
        return getattr(settings, "STRIPE_TEST_SECRET_KEY", "")

    @property
    def LIVE_SECRET_KEY(self):
        return getattr(settings, "STRIPE_LIVE_SECRET_KEY", "")

    @property
    def STRIPE_SECRET_KEY(self):
        if hasattr(settings, "STRIPE_SECRET_KEY"):
            return settings.STRIPE_SECRET_KEY
        from . import settings as djstripe_settings
        if djstripe_settings.STRIPE_LIVE_MODE:
            return self.LIVE_SECRET_KEY
        return self.TEST_SECRET_KEY

    @property
    def STRIPE_PUBLIC_KEY(self):
        from . import settings as djstripe_settings
        if hasattr(settings, "STRIPE_PUBLIC_KEY"):
            return settings.STRIPE_PUBLIC_KEY
        elif djstripe_settings.STRIPE_LIVE_MODE:
            return getattr(settings, "STRIPE_LIVE_PUBLIC_KEY", "")
        return getattr(settings, "STRIPE_TEST_PUBLIC_KEY", "")

    def get_default_api_key(self, livemode):
        """
        Returns the default API key for a value of `livemode`.
        """
        if livemode is None:
            # Livemode is unknown. Use the default secret key.
            return self.STRIPE_SECRET_KEY
        elif livemode:
            # Livemode is true, use the live secret key
            return self.LIVE_SECRET_KEY or self.STRIPE_SECRET_KEY
        else:
            # Livemode is false, use the test secret key
            return self.TEST_SECRET_KEY or self.STRIPE_SECRET_KEY
