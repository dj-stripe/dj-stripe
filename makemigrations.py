import os
import sys

import django

from django.conf import settings


DEFAULT_SETTINGS = dict(
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:'
        }
    },
    DEBUG=True,
    INSTALLED_APPS=[
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        'jsonfield',
        'djstripe',
    ],
    MIDDLEWARE_CLASSES=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware'
    ],
    ROOT_URLCONF='djstripe.urls',
    SITE_ID=1,
    TIME_ZONE='UTC',
    USE_TZ=True,
)


def run(*args):
    if not settings.configured:
        settings.configure(**DEFAULT_SETTINGS)

    django.setup()

    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)

    django.core.management.call_command(
        'makemigrations',
        'djstripe',
        *args
    )


if __name__ == '__main__':
    run(*sys.argv[1:])
