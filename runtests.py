from coverage import coverage
cov = coverage(config_file=True)
cov.erase()
cov.start()

import os
import sys

TESTS_THRESHOLD = 72.00
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
        "tests.apps.testapp"
    ],
    MIDDLEWARE_CLASSES=(
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
    ),
    SITE_ID=1,
    STRIPE_PUBLIC_KEY=os.environ.get("STRIPE_PUBLIC_KEY", "pk_test_lOasUMgiIA701U9wZnL6Zo6a"),
    STRIPE_SECRET_KEY=os.environ.get("STRIPE_SECRET_KEY", "sk_test_nZBY1yjOJ75iFKGjorN29GiA"),
    DJSTRIPE_PLANS={
        "test0": {
            "stripe_plan_id": "test_id_0",
            "name": "Test Plan 0",
            "description": "A test plan",
            "price": 1000,  # $10.00
            "currency": "usd",
            "interval": "month"
        },
        "test": {
            "stripe_plan_id": "test_id",
            "name": "Test Plan 1",
            "description": "Another test plan",
            "price": 2500,  # $25.00
            "currency": "usd",
            "interval": "month"
        },
        "test2": {
            "stripe_plan_id": "test_id_2",
            "name": "Test Plan 2",
            "description": "Yet Another test plan",
            "price": 5000,  # $50.00
            "currency": "usd",
            "interval": "month"
        },
        "unidentified_test_plan": {
            "name": "Unidentified Test Plan",
            "description": "A test plan with no ID.",
            "price": 2500,  # $25.00
            "currency": "usd",
            "interval": "month"
        }
    },
    DJSTRIPE_SUBSCRIPTION_REQUIRED_EXCEPTION_URLS=(
        "(admin)",
        "test_url_name",
        "testapp_namespaced:test_url_namespaced"
    ),
    TEMPLATE_DIRS = [
        os.path.join(TESTS_ROOT, "tests/templates"),
    ],
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

cov.stop()
percentage = round(cov.report(show_missing=True), 2)
cov.html_report(directory='cover')
cov.save()

if percentage < TESTS_THRESHOLD:
    sys.exit("WARNING: YOUR CHANGES HAVE CAUSED TEST COVERAGE TO DROP. " +
             "WAS {old}%, IS NOW {new}%.".format(old=TESTS_THRESHOLD, new=percentage))
