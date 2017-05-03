# -*- coding: utf-8 -*-
"""
.. module:: makemigrations
   :synopsis: dj-stripe - Migrations creation/check tool

   Based on: https://github.com/pinax/pinax-stripe/blob/master/makemigrations.py

.. moduleauthor:: Alex Kavanaugh (@kavdev)
.. moduleauthor:: Lee Skillen (@lskillen)

"""

from __future__ import absolute_import, unicode_literals

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
    """
    Check and/or create dj-stripe Django migrations.

    If --check is present in the arguments then migrations are checked only.
    """
    if not settings.configured:
        settings.configure(**DEFAULT_SETTINGS)

    django.setup()

    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)

    try:
        args = list(args)
        args.pop(args.index('--check'))
        is_check = True
    except ValueError:
        is_check = False

    if is_check:
        django.core.management.call_command(
            'djstripe_has_missing_migrations', *args
        )
    else:
        django.core.management.call_command(
            'makemigrations', 'djstripe', *args
        )


if __name__ == '__main__':
    run(*sys.argv[1:])
