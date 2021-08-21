"""
dj-stripe Context Managers
"""
from contextlib import contextmanager

from .settings import djstripe_settings


@contextmanager
def stripe_temporary_api_version(version, validate=True):
    """
    Temporarily replace the global api_version used in stripe API calls with
     the given value.

    The original value is restored as soon as context exits.
    """

    old_version = djstripe_settings.STRIPE_API_VERSION

    try:
        djstripe_settings.set_stripe_api_version(version, validate=validate)
        yield
    finally:
        # Validation is bypassed since we're restoring a previous value.
        djstripe_settings.set_stripe_api_version(old_version, validate=False)
