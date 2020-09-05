"""
dj-stripe Context Managers
"""
from contextlib import contextmanager


@contextmanager
def stripe_temporary_api_version(version, validate=True):
    """
    Temporarily replace the global api_version used in stripe API calls with
     the given value.

    The original value is restored as soon as context exits.
    """
    from .settings import get_stripe_api_version, set_stripe_api_version

    old_version = get_stripe_api_version()

    try:
        set_stripe_api_version(version, validate=validate)
        yield
    finally:
        # Validation is bypassed since we're restoring a previous value.
        set_stripe_api_version(old_version, validate=False)
