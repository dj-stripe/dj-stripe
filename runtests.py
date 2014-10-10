import os
import sys

TESTS_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

import django
from django.conf import settings

settings.configure(
    TIME_ZONE='America/Los_Angeles',
    DEBUG=True,
    USE_TZ=True,
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": "djstripe",
            "USER": "",
            "PASSWORD": "",
            "HOST": "",
            "PORT": "",
        },
    },
    ROOT_URLCONF="tests.test_urls",
    INSTALLED_APPS=[
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.sites",
        "jsonfield",
        "djstripe",
    ],
    SITE_ID=1,
    STRIPE_PUBLIC_KEY=os.environ.get("STRIPE_PUBLIC_KEY", ""),
    STRIPE_SECRET_KEY=os.environ.get("STRIPE_SECRET_KEY", ""),
    DJSTRIPE_PLANS={},
    DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS=(
        "(admin)",
        "test_url_name",
        "testapp_namespaced:test_url_namespaced"
    ),
    ACCOUNT_SIGNUP_FORM_CLASS='djstripe.forms.StripeSubscriptionSignupForm',
    TEMPLATE_DIRS = [
        os.path.join(TESTS_ROOT, "tests/templates"),
    ]
)

# Avoid AppRegistryNotReady exception
# http://stackoverflow.com/questions/24793351/django-appregistrynotready
if hasattr(django, "setup"):
    django.setup()


from django_nose import NoseTestSuiteRunner

test_runner = NoseTestSuiteRunner(verbosity=1)
failures = test_runner.run_tests(["."])

if failures:
    sys.exit(failures)
