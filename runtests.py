import sys

from django.conf import settings

settings.configure(
    DEBUG=True,
    USE_TZ=True,
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
        }
    },
    ROOT_URLCONF="djstripe.urls",
    INSTALLED_APPS=[
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sites",
        "jsonfield",
        "djstripe",
    ],
    SITE_ID=1,
    STRIPE_PUBLIC_KEY="",
    STRIPE_SECRET_KEY="",
    DJSTRIPE_PLANS={},
    DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS=("(admin)", )
)

from django_nose import NoseTestSuiteRunner

test_runner = NoseTestSuiteRunner(verbosity=1)
failures = test_runner.run_tests(["."])

if failures:
    sys.exit(failures)
