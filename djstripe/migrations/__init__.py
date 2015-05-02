"""
Migrations have been built for Django=>1.7 versions. Alternative migrations
for Django<1.7 users are provided with the ``south_migrations`` dir.

"""

SOUTH_ERROR_MESSAGE = """\n
For South support, customize the SOUTH_MIGRATION_MODULES setting like so:
    SOUTH_MIGRATION_MODULES = {
        'djstripe': 'djstripe.south_migrations',
    }
"""

try:
    from django.db import migrations  # noqa
except ImportError:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(SOUTH_ERROR_MESSAGE)
